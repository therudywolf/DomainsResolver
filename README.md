# 🐺 DomainsResolver

> `D34D1N$1D3` :: numb but alive :: domain to IP pipeline

My resources:
- [Gravatar](https://gravatar.com/therudywolf)
- [OneToThree](https://onetothree.ru)
- [Forest blog](https://t.me/theforestserver)
- [X](https://x.com/therudywolf)
- [GitHub](https://github.com/therudywolf)
- [Twitch](https://twitch.tv/therudywolf)
- [Reddit](https://reddit.com/user/Most-Watercress-6718)
- [Telegram](https://t.me/rudy_wolf)
- [YouTube](https://youtube.com/channel/UCXHkoSlaY5QaNmN_l4t0djQ)

**Domain → IP/CIDR pipeline.** Один файл со списком доменов (и IP/CIDR вперемешку) → резолв → оптимизация → один файл с айпи и подсетями. Опционально пушит результат в Git по изменению.

Автор: **rudywolf**

AGPL v3 Copyleft applies to reuse, modification, and network deployment of derived versions.

---

## Что это

На входе — один TXT (например `input.txt`): домены, wildcard'ы типа `*.domain.com`, CDN, поддомены, плюс сырые IP и CIDR. Пайплайн:

- разбирает строки: IP/CIDR в память, остальное считает доменами;
- гонит домены в асинхронный DNS-резолв (логика из domip — без агрессивного потока, чтобы DNS не банил);
- объединяет резолвленные IP с уже имеющимися IP/CIDR;
- прогоняет через агрегацию из script: дедуп, схлопывание подсетей;
- пишет итог в `output_optimized.txt`.

Запуск **по факту изменения** входного файла: хеш в `.input_hash`, если не поменялся — стая не бежит, лишний резолв не делаем. Раз в день по cron — нормальный вариант.

---

## Стартап (Debian 12, только Docker)

```bash
git clone https://github.com/rudywolf/DMTCDRK.git
cd DMTCDRK
chmod +x start.sh verify.sh
./start.sh
```

`start.sh` сам создаёт `.env` и `input.txt` из примеров, проверяет DNS и push, запускает daemon. Заполни `GIT_PUSH_TOKEN` в `.env` и добавь домены в `input.txt`.

### Команды Docker Compose

| Команда | Режим |
|---------|-------|
| `./start.sh` | Всё: подготовка + проверка + daemon |
| `./verify.sh` | Только проверка DNS и push |
| `docker compose --profile run run --rm run` | Один прогон (input.txt) |
| `docker compose up -d daemon` | Фон (production) |

Частота — в `.env`: `SCHEDULE_INTERVAL_MINUTES=60`.

### Регулярный запуск (cron или daemon)

Чтобы стая выходила раз в день без твоего участия:

```bash
crontab -e
```

Добавь (подставь свой путь к проекту):

```cron
0 3 * * * cd /path/to/DMTCDRK && docker compose --profile run run --rm run >> /var/log/dmtcdrk.log 2>&1
```

**Daemon (рекомендуется):** `docker compose up -d daemon` — фон, проверка каждые `SCHEDULE_INTERVAL_MINUTES` минут. Подходит для 60–100K доменов.

---

## 60–100K доменов (инкрементальный режим)

Для больших списков используй daemon с кэшем:

```bash
# .env
SCHEDULE_INTERVAL_MINUTES=60
USE_DOMAIN_CACHE=1
RESOLVE_PER_RUN=5000
CACHE_TTL_HOURS=24
```

Запуск: `./start.sh` или `docker compose up -d daemon`. Каждый прогон обновляет до 5000 доменов; за 24 часа все 100K перепроверяются.

**Важно:** `DELAY=1.0` и `CONCURRENCY_LIMIT=1` — не уменьшай, иначе бан DNS.

---

## Переменные окружения

Главное в `.env` — **GIT_PUSH_TOKEN** (для пуша по HTTPS). Остальное опционально.

| Переменная | По умолчанию | Назначение |
|------------|--------------|------------|
| `GIT_PUSH_TOKEN` | — | Токен GitHub (PAT). Без него push не будет. |
| `INPUT_FILE` | `input.txt` | Файл со списком доменов/IP/CIDR. |
| `OUTPUT_FILE` | `output_optimized.txt` | Куда писать итог. |
| `DNS_OVER_TLS` | — | `1` — использовать DNS over TLS (шифрование). Иначе обычный DNS из `DNS_POOL`. |
| `DNS_OVER_TLS_SERVERS` | — | Список DoT-серверов: `IP:hostname,IP:hostname`. Пример NextDNS: `45.90.28.61:xxx.dns.nextdns.io,45.90.30.61:xxx.dns.nextdns.io`. |
| `DNS_POOL` | 8.8.8.8, 1.1.1.1, … | Обычные DNS (если DoT выключен), через запятую. |
| `SCHEDULE_INTERVAL_MINUTES` | `60` | Интервал проверки в daemon (мин). 60=час, 1440=день. |
| `USE_DOMAIN_CACHE` | — | `1` — инкрементальный кэш (для daemon, 60–100K доменов). |
| `RESOLVE_PER_RUN` | `5000` | Доменов за один прогон (при USE_DOMAIN_CACHE). |
| `CACHE_TTL_HOURS` | `24` | Через сколько часов перепроверять домен. |
| `CONCURRENCY_LIMIT` | `2` | Сколько DNS-запросов параллельно. |
| `DELAY` | `0.5` | Пауза между запросами (сек). |
| `GIT_BRANCH` | текущая ветка | В какую ветку пушить. |
| `FORCE_RUN` | — | `1` — игнорировать хеш, всегда гонять пайплайн. |
| `KEEP_LAST_OUTPUT_IF_EMPTY` | — | `1` — при пустом результате не затирать старый output. |
| `RESOLVE_AAAA` | — | `1` — ещё и IPv6 (AAAA) в вывод. |
| `LOG_LEVEL` | `INFO` | Уровень логов: DEBUG, INFO, WARNING, ERROR. |
| `FILTER_RESERVED` | `1` | `1` — исключать из вывода зарезервированные/недопустимые адреса (0.0.0.0/8, loopback, multicast, broadcast). |
| `FILTER_PRIVATE` | `0` | `1` — дополнительно исключать приватные диапазоны (10/8, 172.16/12, 192.168/16). |
| `COLLAPSE_IPS_TO_SUBNETS` | `1` | `1` — объединять одиночные IP в подсети (меньше строк, больше CIDR). `0` — оставлять каждый IP отдельной строкой. |

Полный список и тонкости — в [.env.example](.env.example). Развёртывание на сервере по шагам — [DEPLOY.md](DEPLOY.md).

### DNS over TLS (DoT)

Чтобы резолвить домены через зашифрованный DoT (например NextDNS), в `.env` добавь:

```bash
DNS_OVER_TLS=1
DNS_OVER_TLS_SERVERS=45.90.28.61:твой-профиль.dns.nextdns.io,45.90.30.61:твой-профиль.dns.nextdns.io
```

Формат: через запятую пары `IP:hostname` (hostname — для проверки TLS). Без DoT используется обычный DNS из `DNS_POOL`.

---

## Режимы

- **Обычный запуск:** `./run.sh` или `python pipeline.py` — полный цикл (чтение → резолв → оптимизация → запись). При изменении output/hash — git add/commit/push.
- **Только проверить вход:** `python pipeline.py --dry-run` — покажет, сколько IP/CIDR и доменов, без DNS и без записи.
- **Гнать принудительно:** `FORCE_RUN=1 ./run.sh` — не смотреть на хеш, всегда выполнять пайплайн.

---

## Результат

- **output_optimized.txt** — по одной строке: IP или CIDR, отсортировано. Запись атомарная (через .tmp).
- Из вывода **исключаются недопустимые для маршрутизации адреса**: 0.0.0.0/8, loopback (127.0.0.0/8), multicast (224.0.0.0/4), reserved (240.0.0.0/4), broadcast (255.255.255.255). Опционально можно отфильтровать и приватные диапазоны (см. `FILTER_PRIVATE`). Одиночные IP по умолчанию **объединяются в подсети** (collapse), чтобы уменьшить число строк и увеличить долю CIDR.
- В конце прогона в консоль выводится строка **METRICS** с числами (домены, IP, время и т.д.).

---

## Ограничения

- По умолчанию только IPv4; для IPv6 выставить `RESOLVE_AAAA=1`.
- При пустом результате с `KEEP_LAST_OUTPUT_IF_EMPTY=1` старый файл не перезаписывается.

---

## Тесты

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## Структура проекта

- `pipeline.py` — основной пайплайн (чтение, классификация, резолв, оптимизация, запись).
- `ip_utils.py` — парсинг IP/CIDR и `optimize_list`.
- `script.py` — отдельный консолидатор по директории (использует ip_utils).
- `run.sh` — проверка хеша, запуск пайплайна, обновление `.input_hash`, вызов sync.
- `scheduler.sh` — цикл для daemon: запуск `run.sh` каждые N минут.
- `start.sh` — единая точка входа: подготовка + проверка + daemon.
- `deploy.sh` — алиас для `start.sh`.
- `verify.sh` — проверка DNS и push через Docker Compose.
- `sync.sh` — git add/commit/push при изменении output/hash; откат origin после пуша.
