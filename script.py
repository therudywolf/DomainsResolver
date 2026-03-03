import re
from ipaddress import ip_network, ip_address, AddressValueError
from pathlib import Path
from collections import defaultdict

# === КОНФИГ ===
OUTPUT_PREFIX = "ip_consolidated"
MAX_LINES_PER_FILE = 10000

# === ВАЛИДАЦИЯ ===
def is_valid_ip(ip_str: str) -> bool:
    parts = ip_str.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False

def parse_entry(entry):
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
    else:
        if not is_valid_ip(entry):
            return None
        try:
            return ip_address(entry)
        except AddressValueError:
            return None

# === СБОР ===
pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b")

def extract_ips_and_cidrs(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read()
    except Exception as e:
        print(f"\n[ERROR] {file_path}: {e}")
        return []
    return pattern.findall(txt)

def scan_directory(root_dir="."):
    files = list(Path(root_dir).rglob("*.txt"))
    total = len(files)
    print(f"[SCAN] Найдено {total} файлов")
    all_entries = []
    for idx, p in enumerate(files, 1):
        percent = (idx / total) * 100 if total else 100
        print(f"\r[{idx}/{total}] {percent:5.1f}%  {p}", end="", flush=True)
        all_entries.extend(extract_ips_and_cidrs(p))
    print(f"\n[INFO] Извлечено {len(all_entries)} сырых записей")
    return all_entries

# === ОПТИМ И АГРЕГАЦИЯ ===
def optimize_list(raw_entries):
    networks = set()
    ips = set()
    invalid = 0

    print("[PARSE] Валидация и разбор...")
    total = len(raw_entries)
    for idx, e in enumerate(raw_entries, 1):
        if idx % 5000 == 0 or idx == total:
            print(f"\r  Обработано {idx}/{total}", end="", flush=True)
        parsed = parse_entry(e)
        if parsed is None:
            invalid += 1
            continue
        if parsed.__class__.__name__ == "IPv4Network":
            networks.add(parsed)
        else:
            ips.add(parsed)
    print(f"\n[INFO] Отброшено невалидных: {invalid}")
    print(f"[INFO] Подсетей: {len(networks)} | Отдельных IP: {len(ips)}")

    # агрегируем сети: убираем те, что полностью лежат в других
    print("[OPTIMIZE] Агрегация подсетей...")
    sorted_nets = sorted(networks, key=lambda n: (n.network_address, -n.prefixlen))
    unique_nets = []
    for net in sorted_nets:
        if not any(net.subnet_of(u) for u in unique_nets):
            unique_nets.append(net)
    print(f"[INFO] Уникальных подсетей после агрегации: {len(unique_nets)}")

    # выкидываем IP, которые уже покрыты сетями
    print("[FILTER] Фильтрация IP по подсетям...")
    filtered_ips = []
    total_ips = len(ips)
    for idx, ip in enumerate(ips, 1):
        if idx % 5000 == 0 or idx == total_ips:
            print(f"\r  Проверено IP {idx}/{total_ips}", end="", flush=True)
        if not any(ip in net for net in unique_nets):
            filtered_ips.append(ip)
    print(f"\n[INFO] IP вне подсетей: {len(filtered_ips)}")

    # итоговый список строк
    result = [str(n) for n in unique_nets] + [str(ip) for ip in filtered_ips]

    # единый ключ сортировки: (int(address), prefix)
    def sort_key(entry: str):
        if "/" in entry:
            net = ip_network(entry, strict=False)
            return (int(net.network_address), net.prefixlen)
        else:
            ip = ip_address(entry)
            return (int(ip), 32)

    result.sort(key=sort_key)
    return result

# === ВЫВОД ===
def write_chunks(entries, prefix):
    total = len(entries)
    if total == 0:
        print("[OUTPUT] Нечего писать, список пуст")
        return
    chunks = (total + MAX_LINES_PER_FILE - 1) // MAX_LINES_PER_FILE
    for i in range(chunks):
        start = i * MAX_LINES_PER_FILE
        end = min(start + MAX_LINES_PER_FILE, total)
        filename = f"{prefix}_{i+1}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(entries[start:end]))
        print(f"[WRITE] {filename} ({end - start} строк)")

def print_stats(entries):
    nets = sum(1 for e in entries if "/" in e)
    ips = len(entries) - nets
    mask_dist = defaultdict(int)
    for e in entries:
        if "/" in e:
            mask_dist[e.split("/")[1]] += 1
    print("\n=== СТАТИСТИКА ===")
    print(f"Всего записей: {len(entries)}")
    print(f"  └ Подсети: {nets}")
    print(f"  └ Отдельные IP: {ips}")
    if mask_dist:
        print("\nРаспределение по маскам:")
        for m in sorted(mask_dist, key=int):
            print(f"  /{m}: {mask_dist[m]} шт")

# === MAIN ===
if __name__ == "__main__":
    print("=" * 60)
    print("IP/CIDR CONSOLIDATOR v2.1")
    print("=" * 60)

    raw = scan_directory(".")
    optimized = optimize_list(raw)
    print_stats(optimized)
    print("\n[OUTPUT] Запись файлов...")
    write_chunks(optimized, OUTPUT_PREFIX)

    print("\n" + "=" * 60)
    print("[DONE] ✓ Завершено")
    print("=" * 60)
