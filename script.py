import re
from pathlib import Path

from ip_utils import optimize_list, parse_entry, print_stats

# === КОНФИГ ===
OUTPUT_PREFIX = "ip_consolidated"
MAX_LINES_PER_FILE = 10000

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
