#!/usr/bin/env python3
"""
Unified pipeline: read input.txt (domains + IP/CIDR), resolve domains async,
merge with IP/CIDR, optimize list, write output_optimized.txt.
Cron-friendly, type-hinted, strict error handling.
"""
from __future__ import annotations

import asyncio
import os
import sys
import random
from typing import List, Set, Tuple

# Windows event loop fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

try:
    import dns.asyncresolver
    from dns.exception import Timeout
except ImportError:
    print("[ERROR] dnspython required: pip install dnspython", file=sys.stderr)
    sys.exit(1)

from script import parse_entry, optimize_list

# --- Config (env override) ---
INPUT_FILE = os.environ.get("INPUT_FILE", "input.txt")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "output_optimized.txt")
CONCURRENCY_LIMIT = int(os.environ.get("CONCURRENCY_LIMIT", "1"))
DELAY = float(os.environ.get("DELAY", "0.9"))
MAX_RETRIES = 3

DNS_POOL = [
    "8.8.8.8", "8.8.4.4",
    "1.1.1.1", "1.0.0.1",
    "9.9.9.9", "149.112.112.112",
    "208.67.222.222", "208.67.220.220",
    "77.88.8.8", "77.88.8.1",
    "94.140.14.14", "94.140.15.15",
]


def read_and_classify(input_path: str) -> Tuple[List[str], List[str]]:
    """Read input file, return (ip_cidr_entries, domains)."""
    try:
        with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except OSError as e:
        print(f"[ERROR] Cannot read {input_path}: {e}", file=sys.stderr)
        sys.exit(1)

    ip_cidr: List[str] = []
    domains: List[str] = []
    for line in lines:
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        parsed = parse_entry(raw)
        if parsed is None:
            domains.append(raw)
            continue
        if parsed.__class__.__name__ == "IPv4Network":
            ip_cidr.append(str(parsed))
        else:
            ip_cidr.append(str(parsed))
    return ip_cidr, domains


async def resolve_domain(
    domain: str,
    sem: asyncio.Semaphore,
    ip_set: Set[str],
    delay: float,
    max_retries: int,
) -> None:
    """Resolve one domain (A record), support wildcard *. -> www., add IPs to ip_set."""
    raw_domain = domain.strip()
    if not raw_domain:
        return
    if raw_domain.startswith("*."):
        clean_domain = raw_domain.replace("*.", "www.", 1)
    else:
        clean_domain = raw_domain

    async with sem:
        for attempt in range(max_retries):
            try:
                resolver = dns.asyncresolver.Resolver()
                resolver.nameservers = random.sample(DNS_POOL, min(3, len(DNS_POOL)))
                resolver.lifetime = 5.0
                answers = await resolver.resolve(clean_domain, "A")
                addrs = [rdata.address for rdata in answers]
                for ip in addrs:
                    ip_set.add(ip)
                if addrs:
                    print(f"[+] {raw_domain} -> {addrs[0]}" + (f" (+{len(addrs)-1})" if len(addrs) > 1 else ""))
                await asyncio.sleep(delay)
                return
            except Timeout:
                if attempt < max_retries - 1:
                    print(f"[*] {raw_domain} -> TIMEOUT (retry {attempt + 2})")
                    await asyncio.sleep(delay * 2)
                else:
                    print(f"[-] {raw_domain} -> FAIL (timeout)")
            except Exception as e:
                print(f"[-] {raw_domain} -> FAIL ({type(e).__name__})")
                break


async def resolve_all(domains: List[str]) -> Set[str]:
    """Resolve all domains asynchronously, return set of IP strings."""
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    ip_set: Set[str] = set()
    tasks = [
        resolve_domain(d, sem, ip_set, DELAY, MAX_RETRIES)
        for d in domains
    ]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    return ip_set


def main_sync() -> None:
    """Synchronous entry: read, classify, resolve, merge, optimize, write."""
    if not os.path.exists(INPUT_FILE):
        print(f"[ERROR] {INPUT_FILE} not found", file=sys.stderr)
        sys.exit(1)

    print(f"[LOAD] Reading {INPUT_FILE}...")
    ip_cidr, domains = read_and_classify(INPUT_FILE)
    print(f"[INFO] IP/CIDR: {len(ip_cidr)} | Domains: {len(domains)}")

    resolved_ips: Set[str] = set()
    if domains:
        print(f"[RESOLVE] Starting DNS resolution ({len(domains)} domains)...")
        resolved_ips = asyncio.run(resolve_all(domains))
        print(f"[INFO] Resolved {len(resolved_ips)} unique IPs")

    merged: List[str] = ip_cidr + list(resolved_ips)
    if not merged:
        print("[WARN] No IP/CIDR entries to optimize")
        merged = []

    print("[OPTIMIZE] Aggregating and deduplicating...")
    try:
        optimized = optimize_list(merged)
    except Exception as e:
        print(f"[ERROR] optimize_list failed: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(optimized))
        print(f"[SAVE] {OUTPUT_FILE} ({len(optimized)} entries)")
    except OSError as e:
        print(f"[ERROR] Cannot write {OUTPUT_FILE}: {e}", file=sys.stderr)
        sys.exit(1)

    print("[DONE] Pipeline finished successfully.")


if __name__ == "__main__":
    try:
        main_sync()
    except KeyboardInterrupt:
        print("\n[STOP] Interrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
