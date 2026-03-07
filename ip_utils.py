"""
Shared IP/CIDR parsing and list optimization. Used by pipeline.py and script.py.
"""
from __future__ import annotations

from collections import defaultdict
from ipaddress import (
    AddressValueError,
    IPv4Address,
    IPv4Network,
    collapse_addresses,
    ip_address,
    ip_network,
)
from typing import List, Optional, Union


def is_valid_ip(ip_str: str) -> bool:
    """Check if string is a valid IPv4 address."""
    parts = ip_str.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


def parse_entry(entry: str) -> Optional[Union[IPv4Network, IPv4Address]]:
    """Parse a string as IPv4 address or CIDR; return None if invalid or empty."""
    entry = entry.strip()
    if not entry:
        return None
    if "/" in entry:
        ip_part, mask = entry.split("/", 1)
        if not is_valid_ip(ip_part):
            return None
        try:
            mask_int = int(mask)
            if not (0 <= mask_int <= 32):
                return None
            return ip_network(f"{ip_part}/{mask_int}", strict=False)
        except (ValueError, AddressValueError):
            return None
    if not is_valid_ip(entry):
        return None
    try:
        return ip_address(entry)
    except AddressValueError:
        return None


# Reserved/unsuitable for routing (filtered by default)
_RESERVED_NETWORKS = [
    ip_network("0.0.0.0/8"),      # current network / "any"
    ip_network("127.0.0.0/8"),   # loopback
    ip_network("224.0.0.0/4"),   # multicast
    ip_network("240.0.0.0/4"),   # reserved (includes 255.255.255.255)
]

# Private ranges (filtered only when FILTER_PRIVATE=1)
_PRIVATE_NETWORKS = [
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
]


def is_reserved_or_unsuitable_for_routing(
    parsed: Union[IPv4Address, IPv4Network],
    filter_private: bool = False,
) -> bool:
    """Return True if the address/network should be excluded from routing blocklist."""
    if isinstance(parsed, IPv4Address):
        net = ip_network(str(parsed) + "/32")
    else:
        net = parsed
    if any(net.overlaps(r) for r in _RESERVED_NETWORKS):
        return True
    if filter_private and any(net.overlaps(p) for p in _PRIVATE_NETWORKS):
        return True
    return False


def optimize_list(
    raw_entries: List[str],
    *,
    filter_reserved: bool = True,
    filter_private: bool = False,
    collapse_ips: bool = True,
) -> List[str]:
    """
    Validate, deduplicate, aggregate subnets, filter IPs covered by networks,
    sort. Optionally filter reserved/invalid addresses and collapse single IPs into subnets.
    Returns sorted list of "ip" or "cidr/mask" strings.
    """
    networks: set = set()
    ips: set = set()
    invalid = 0
    reserved_filtered = 0

    print("[PARSE] Валидация и разбор...")
    total = len(raw_entries)
    for idx, e in enumerate(raw_entries, 1):
        if idx % 5000 == 0 or idx == total:
            print(f"\r  Обработано {idx}/{total}", end="", flush=True)
        parsed = parse_entry(e)
        if parsed is None:
            invalid += 1
            continue
        if filter_reserved and is_reserved_or_unsuitable_for_routing(parsed, filter_private):
            reserved_filtered += 1
            continue
        if parsed.__class__.__name__ == "IPv4Network":
            networks.add(parsed)
        else:
            ips.add(parsed)
    print(f"\n[INFO] Отброшено невалидных: {invalid} | зарезервированных: {reserved_filtered}")
    print(f"[INFO] Подсетей: {len(networks)} | Отдельных IP: {len(ips)}")

    print("[OPTIMIZE] Агрегация подсетей...")
    sorted_nets = sorted(networks, key=lambda n: (n.network_address, -n.prefixlen))
    unique_nets: List = []
    for net in sorted_nets:
        if not any(net.subnet_of(u) for u in unique_nets):
            unique_nets.append(net)
    print(f"[INFO] Уникальных подсетей после агрегации: {len(unique_nets)}")

    print("[FILTER] Фильтрация IP по подсетям...")
    filtered_ips: List = []
    total_ips = len(ips)
    for idx, ip in enumerate(ips, 1):
        if idx % 5000 == 0 or idx == total_ips:
            print(f"\r  Проверено IP {idx}/{total_ips}", end="", flush=True)
        if not any(ip in net for net in unique_nets):
            filtered_ips.append(ip)
    print(f"\n[INFO] IP вне подсетей: {len(filtered_ips)}")

    if collapse_ips and filtered_ips:
        print("[COLLAPSE] Объединение IP в подсети...")
        all_nets: List[IPv4Network] = list(unique_nets) + [
            ip_network(str(ip) + "/32") for ip in filtered_ips
        ]
        collapsed = list(collapse_addresses(all_nets))
        result = [str(n) for n in collapsed]
        print(f"[INFO] После объединения: {len(result)} записей")
    else:
        result = [str(n) for n in unique_nets] + [str(ip) for ip in filtered_ips]

    def sort_key(entry: str):
        if "/" in entry:
            net = ip_network(entry, strict=False)
            return (int(net.network_address), net.prefixlen)
        addr = ip_address(entry)
        return (int(addr), 32)

    result.sort(key=sort_key)
    return result


def print_stats(entries: List[str]) -> None:
    """Print human-readable stats for optimized list."""
    nets = sum(1 for e in entries if "/" in e)
    ip_count = len(entries) - nets
    mask_dist: dict = defaultdict(int)
    for e in entries:
        if "/" in e:
            mask_dist[e.split("/")[1]] += 1
    print("\n=== СТАТИСТИКА ===")
    print(f"Всего записей: {len(entries)}")
    print(f"  └ Подсети: {nets}")
    print(f"  └ Отдельные IP: {ip_count}")
    if mask_dist:
        print("\nРаспределение по маскам:")
        for m in sorted(mask_dist, key=int):
            print(f"  /{m}: {mask_dist[m]} шт")
