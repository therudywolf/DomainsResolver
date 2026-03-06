"""
DEPRECATED: Для резолва доменов используй pipeline.py (Docker + WireGuard/DoT).
Этот скрипт оставлен для совместимости; конфиг жёстко задан (dodep.txt, DNS_POOL).
"""
import asyncio
import os
import sys
import random
import dns.asyncresolver
from dns.exception import Timeout

# Жесткий фикс для Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Твои настройки стелса
INPUT_FILE = 'dodep.txt'
OUTPUT_PREFIX = 'ips_chunk_'
CHUNK_SIZE = 10000
CONCURRENCY_LIMIT = 1  
DELAY = 0.9  
MAX_RETRIES = 3

DNS_POOL = [
    '8.8.8.8', '8.8.4.4',         
    '1.1.1.1', '1.0.0.1',         
    '9.9.9.9', '149.112.112.112', 
    '208.67.222.222', '208.67.220.220', 
    '77.88.8.8', '77.88.8.1',     
    '94.140.14.14', '94.140.15.15' 
]

async def resolve_domain(domain, sem, ip_set):
    raw_domain = domain.strip()
    if not raw_domain:
        return

    # Подмена wildcard на рабочий субдомен, чтобы пробить CDN
    if raw_domain.startswith('*.'):
        clean_domain = raw_domain.replace('*.', 'www.', 1)
    else:
        clean_domain = raw_domain

    async with sem:
        for attempt in range(MAX_RETRIES):
            try:
                resolver = dns.asyncresolver.Resolver()
                resolver.nameservers = random.sample(DNS_POOL, 3)
                resolver.lifetime = 5.0 # Даем больше времени на ответ от тяжелых CDN
                
                answers = await resolver.resolve(clean_domain, 'A')
                for rdata in answers:
                    ip = rdata.address
                    ip_set.add(ip)
                    print(f"[+] {raw_domain} ({clean_domain}) -> {ip}")
                
                await asyncio.sleep(DELAY)
                return 

            except Timeout:
                if attempt < MAX_RETRIES - 1:
                    print(f"[*] {raw_domain} -> TIMEOUT. Отходим (Попытка {attempt + 2})...")
                    await asyncio.sleep(DELAY * 2) 
                else:
                    print(f"[-] {raw_domain} -> DEAD (Броня не пробита)")
            except Exception as e:
                err_type = type(e).__name__
                print(f"[-] {raw_domain} -> DEAD ({err_type})")
                break 

async def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Файл {INPUT_FILE} не найден.")
        return

    with open(INPUT_FILE, 'r') as f:
        domains = f.readlines()

    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    ip_set = set()

    print(f"Стая: {len(domains)}. Медленный режим активирован. Выкуриваем CDN...")
    
    tasks = [resolve_domain(d, sem, ip_set) for d in domains]
    
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass

    unique_ips = list(ip_set)
    total_ips = len(unique_ips)
    print(f"\n[ОХОТА ЗАВЕРШЕНА] Вырвано {total_ips} IP. Дроблю...")

    for i in range(0, total_ips, CHUNK_SIZE):
        chunk = unique_ips[i:i + CHUNK_SIZE]
        file_name = f"{OUTPUT_PREFIX}{(i//CHUNK_SIZE) + 1}.txt"
        with open(file_name, 'w') as f:
            f.write('\n'.join(chunk))
        print(f"[SAVE] {file_name} ({len(chunk)} IP) сохранен.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOP] Принудительный стоп. Уходим в туман.")