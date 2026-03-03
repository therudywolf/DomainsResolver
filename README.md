# DMTCDRK

**Domain → IP/CIDR pipeline.** Один файл со списком доменов (и IP/CIDR вперемешку) → резолв → оптимизация → один файл с айпи и подсетями. Опционально пушит результат в Git по изменению.

Автор: **rudywolf**

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

## Стартап-гайд (с нуля)

### 1. Клонируй / скопируй проект

```bash
git clone https://github.com/rudywolf/DMTCDRK.git
cd DMTCDRK
```

### 2. Файл со списком

Создай `input.txt` в корне — по одной строке: домен, `*.domain.com`, IP или CIDR. Пустые строки и строки с `#` игнорируются.

```bash
echo "example.com" >> input.txt
echo "192.168.1.0/24" >> input.txt
```

### 3. Окружение

```bash
cp .env.example .env
```

Открой `.env`. Минимум — для автоматического пуша в Git нужен токен:

- Зайди на https://github.com/settings/tokens
- **Generate new token (classic)**, права — `repo`
- Скопируй токен и вставь в `.env`:

```bash
GIT_PUSH_TOKEN=ghp_твой_токен_сюда
```

Остальное в `.env` можно не трогать (дефолты ок).

### 4. Первый запуск — проверка

```bash
./verify.sh
```

Резолвит несколько тестовых доменов (example.com, github.com, cloudflare.com) с отладкой (LOG_LEVEL=DEBUG), проверяет доступность git push (dry-run). Убедись, что всё работает перед `./run.sh` или `deploy.sh`.

Без Python на хосте: `./deploy.sh` сам запустит проверку через Docker при первом запуске.

### 5. Запуск

**Docker Compose — два режима:**

| Команда | Режим |
|---------|-------|
| `docker compose run --rm app` | Один прогон |
| `docker compose up -d daemon` | Фон (production) |

Частота проверки — в `.env`: `SCHEDULE_INTERVAL_MINUTES=60` (каждый час) или `1440` (раз в день).

**Без Docker:**

```bash
pip install -r requirements.txt
chmod +x run.sh sync.sh
./run.sh
```

Первый прогон: резолв доменов, оптимизация, запись `output_optimized.txt` и `.input_hash`. Если что-то изменилось — `sync.sh` сделает commit и push (если задан `GIT_PUSH_TOKEN`).

### 6. Регулярный запуск (cron или daemon)

Чтобы стая выходила раз в день без твоего участия:

```bash
crontab -e
```

Добавь (подставь свой путь к проекту):

```cron
0 3 * * * cd /path/to/DMTCDRK && docker compose run --rm app ./run.sh >> /var/log/dmtcdrk.log 2>&1
```

Без Docker:

```cron
0 3 * * * cd /path/to/DMTCDRK && ./run.sh >> /var/log/dmtcdrk.log 2>&1
```

**Вариант A — Docker daemon (рекомендуется):** `docker compose up daemon` — работает в фоне, проверяет каждые `SCHEDULE_INTERVAL_MINUTES` минут. Подходит для 60–100K доменов (инкрементальный кэш).

**Вариант B — cron:** Резолв по полному списку пойдёт только когда изменится `input.txt`; иначе скрипт просто выйдет без лишней нагрузки.

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

Запуск: `docker compose up daemon`. Каждый прогон обновляет до 5000 доменов; за 24 часа все 100K перепроверяются. Нагрузка распределена равномерно.

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
- `deploy.sh` — развёртывание на сервере: сборка + `docker compose up -d daemon`.
- `verify.sh` — первый запуск: проверка DNS и push с отладкой.
- `sync.sh` — git add/commit/push при изменении output/hash; откат origin после пуша.
