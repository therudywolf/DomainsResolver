#!/usr/bin/env python3
"""
Unified pipeline: read input.txt (domains + IP/CIDR), resolve domains async,
merge with IP/CIDR, optimize list, write output_optimized.txt.
Cron-friendly, type-hinted, strict error handling.
"""
from __future__ import annotations

import asyncio
import argparse
import os
import sys
import random
import time
from typing import List, Set, Tuple

from ipaddress import ip_address as ip_parse

# Windows event loop fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

try:
    import dns.asyncresolver
    from dns.exception import Timeout
except ImportError:
    print("[ERROR] dnspython required: pip install dnspython", file=sys.stderr)
    sys.exit(1)

from ip_utils import parse_entry, optimize_list

INPUT_FILE = os.environ.get("INPUT_FILE", "input.txt")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "output_optimized.txt")
CONCURRENCY_LIMIT = int(os.environ.get("CONCURRENCY_LIMIT", "1"))
DELAY = float(os.environ.get("DELAY", "0.9"))
RESOLVER_TIMEOUT = float(os.environ.get("RESOLVER_TIMEOUT", "5.0"))
MAX_RETRIES = 3
RESOLVE_AAAA = os.environ.get("RESOLVE_AAAA", "").strip().lower() in ("1", "true", "yes")

_dns_pool_env = os.environ.get("DNS_POOL", "").strip()
if _dns_pool_env:
    DNS_POOL = [s.strip() for s in _dns_pool_env.split(",") if s.strip()]
else:
    DNS_POOL = [
        "8.8.8.8", "8.8.4.4",
        "1.1.1.1", "1.0.0.1",
        "9.9.9.9", "149.112.112.112",
        "208.67.222.222", "208.67.220.220",
        "77.88.8.8", "77.88.8.1",
        "94.140.14.14", "94.140.15.15",
    ]
if not DNS_POOL:
    DNS_POOL = ["8.8.8.8", "1.1.1.1"]

_LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
LOG_LEVEL = _LOG_LEVELS.get(os.environ.get("LOG_LEVEL", "INFO").upper(), 20)


def _log(level: str, msg: str, **kwargs: str) -> None:
    lvl = _LOG_LEVELS.get(level.upper(), 20)
    if lvl >= LOG_LEVEL:
        extra = " ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        print(f"[{level}] {msg}" + (" " + extra if extra else ""))


def read_and_classify(input_path: str) -> Tuple[List[str], List[str]]:
    """Read input file, return (ip_cidr_entries, domains). Normalizes and deduplicates."""
    try:
        with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except OSError as e:
        print(f"[ERROR] Cannot read {input_path}: {e}", file=sys.stderr)
        sys.exit(1)

    ip_cidr_set: Set[str] = set()
    domain_set: Set[str] = set()
    for line in lines:
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        parsed = parse_entry(raw)
        if parsed is None:
            domain_set.add(raw.lower().strip())
            continue
        if parsed.__class__.__name__ == "IPv4Network":
            ip_cidr_set.add(str(parsed))
        else:
            ip_cidr_set.add(str(parsed))
    return list(ip_cidr_set), list(domain_set)


async def resolve_domain(
    domain: str,
    sem: asyncio.Semaphore,
    ip_set: Set[str],
    delay: float,
    max_retries: int,
    resolver_timeout: float,
    backoff_state: dict,
    resolve_stats: dict,
    resolve_aaaa: bool,
) -> None:
    """Resolve one domain (A record, optionally AAAA), support wildcard *. -> www., add IPs to ip_set."""
    raw_domain = domain.strip()
    if not raw_domain:
        return
    if raw_domain.startswith("*."):
        clean_domain = raw_domain.replace("*.", "www.", 1)
    else:
        clean_domain = raw_domain

    effective_delay = delay * 2 if backoff_state.get("backoff_remaining", 0) > 0 else delay

    async with sem:
        for attempt in range(max_retries):
            try:
                resolver = dns.asyncresolver.Resolver()
                resolver.nameservers = random.sample(DNS_POOL, min(3, len(DNS_POOL)))
                resolver.lifetime = resolver_timeout
                answers = await resolver.resolve(clean_domain, "A")
                addrs = [rdata.address for rdata in answers]
                for ip in addrs:
                    ip_set.add(ip)
                if resolve_aaaa:
                    try:
                        aaaa = await resolver.resolve(clean_domain, "AAAA")
                        for rdata in aaaa:
                            ip_set.add(rdata.address)
                        await asyncio.sleep(effective_delay * 0.5)
                    except Exception:
                        pass
                backoff_state["consecutive_fail"] = 0
                if addrs:
                    resolve_stats["ok"] = resolve_stats.get("ok", 0) + 1
                    print(f"[+] {raw_domain} -> {addrs[0]}" + (f" (+{len(addrs)-1})" if len(addrs) > 1 else ""))
                else:
                    resolve_stats["ok"] = resolve_stats.get("ok", 0) + 1
                await asyncio.sleep(effective_delay)
                if backoff_state.get("backoff_remaining", 0) > 0:
                    backoff_state["backoff_remaining"] -= 1
                return
            except Timeout:
                backoff_state["consecutive_fail"] = backoff_state.get("consecutive_fail", 0) + 1
                if backoff_state["consecutive_fail"] >= 5:
                    backoff_state["backoff_remaining"] = backoff_state.get("backoff_remaining", 0) + 10
                if attempt < max_retries - 1:
                    print(f"[*] {raw_domain} -> TIMEOUT (retry {attempt + 2})")
                    await asyncio.sleep(delay * 2)
                else:
                    print(f"[-] {raw_domain} -> FAIL (timeout)")
                    resolve_stats["fail"] = resolve_stats.get("fail", 0) + 1
            except Exception as e:
                backoff_state["consecutive_fail"] = backoff_state.get("consecutive_fail", 0) + 1
                if backoff_state["consecutive_fail"] >= 5:
                    backoff_state["backoff_remaining"] = backoff_state.get("backoff_remaining", 0) + 10
                print(f"[-] {raw_domain} -> FAIL ({type(e).__name__})")
                resolve_stats["fail"] = resolve_stats.get("fail", 0) + 1
                break


async def resolve_all(domains: List[str]) -> Tuple[Set[str], dict]:
    """Resolve all domains asynchronously. Returns (set of IP strings, stats dict)."""
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    ip_set: Set[str] = set()
    backoff_state: dict = {"consecutive_fail": 0, "backoff_remaining": 0}
    resolve_stats: dict = {"ok": 0, "fail": 0}
    tasks = [
        resolve_domain(d, sem, ip_set, DELAY, MAX_RETRIES, RESOLVER_TIMEOUT, backoff_state, resolve_stats, RESOLVE_AAAA)
        for d in domains
    ]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    return ip_set, resolve_stats


def main_sync() -> None:
    """Synchronous entry: read, classify, resolve (unless --dry-run), merge, optimize, write."""
    parser = argparse.ArgumentParser(description="Resolve domains and optimize IP/CIDR list.")
    parser.add_argument("--dry-run", action="store_true", help="Only read and classify input, no resolve or write.")
    args = parser.parse_args()
    dry_run = args.dry_run
    start_time = time.monotonic()

    if not os.path.exists(INPUT_FILE):
        print(f"[ERROR] {INPUT_FILE} not found", file=sys.stderr)
        sys.exit(1)

    _log("INFO", f"Reading {INPUT_FILE}...")
    ip_cidr, domains = read_and_classify(INPUT_FILE)
    _log("INFO", f"IP/CIDR: {len(ip_cidr)} | Domains: {len(domains)}")

    if dry_run:
        _log("INFO", "DRY-RUN: Skipping resolve and write.")
        return

    resolved_ips: Set[str] = set()
    resolve_stats: dict = {"ok": 0, "fail": 0}
    if domains:
        _log("INFO", f"Starting DNS resolution ({len(domains)} domains)...")
        resolved_ips, resolve_stats = asyncio.run(resolve_all(domains))
        _log("INFO", f"Resolved {len(resolved_ips)} unique IPs")

    def _is_ipv4(s: str) -> bool:
        try:
            return ip_parse(s).version == 4
        except Exception:
            return False

    def _is_ipv6(s: str) -> bool:
        try:
            return ip_parse(s).version == 6
        except Exception:
            return False

    ipv4_resolved = [ip for ip in resolved_ips if _is_ipv4(ip)]
    ipv6_only = sorted(ip for ip in resolved_ips if _is_ipv6(ip))
    merged: List[str] = ip_cidr + ipv4_resolved
    if not merged:
        print("[WARN] No IP/CIDR entries to optimize")
        merged = []

    print("[OPTIMIZE] Aggregating and deduplicating...")
    try:
        optimized = optimize_list(merged)
        optimized = optimized + ipv6_only
    except Exception as e:
        print(f"[ERROR] optimize_list failed: {e}", file=sys.stderr)
        sys.exit(1)

    keep_if_empty = os.environ.get("KEEP_LAST_OUTPUT_IF_EMPTY", "").strip().lower() in ("1", "true", "yes")
    if not optimized and keep_if_empty:
        print("[WARN] Optimized list is empty; keeping existing output (KEEP_LAST_OUTPUT_IF_EMPTY=1).")
        return
    if not optimized:
        print("[WARN] Optimized list is empty; writing empty output.")

    try:
        tmp_path = OUTPUT_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write("\n".join(optimized))
        os.replace(tmp_path, OUTPUT_FILE)
        _log("INFO", f"Wrote {OUTPUT_FILE} ({len(optimized)} entries)")
    except OSError as e:
        print(f"[ERROR] Cannot write {OUTPUT_FILE}: {e}", file=sys.stderr)
        sys.exit(1)

    duration_sec = round(time.monotonic() - start_time, 1)
    print(
        f"METRICS domains_in={len(domains)} domains_ok={resolve_stats.get('ok', 0)} "
        f"domains_fail={resolve_stats.get('fail', 0)} ips_resolved={len(resolved_ips)} "
        f"ips_cidr_input={len(ip_cidr)} optimized_entries={len(optimized)} duration_sec={duration_sec}"
    )
    _log("INFO", "Pipeline finished successfully.")


if __name__ == "__main__":
    try:
        main_sync()
    except KeyboardInterrupt:
        print("\n[STOP] Interrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
