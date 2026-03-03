# Развёртывание на сервере

Production: скопировать проект → заполнить `.env` → `./deploy.sh`

---

## Быстрый старт (production)

```bash
git clone https://github.com/rudywolf/DMTCDRK.git
cd DMTCDRK
cp .env.example .env
# Отредактируй .env: GIT_PUSH_TOKEN, DNS_OVER_TLS_SERVERS (если NextDNS)
chmod +x deploy.sh run.sh sync.sh scheduler.sh verify.sh
./verify.sh          # первый раз: проверка DNS и push с отладкой
./deploy.sh          # deploy запустит verify автоматически при первом запуске
```

Daemon запустится в фоне. Логи: `docker compose logs -f daemon`

---

## 1. Копирование

```bash
git clone https://github.com/rudywolf/DMTCDRK.git
cd DMTCDRK
```

Либо архив: `git archive -o DMTCDRK.zip HEAD`, перенести на сервер, распаковать.

---

## 2. Токен для Git push

Создаётся только в GitHub:

1. https://github.com/settings/tokens
2. **Generate new token (classic)**, право `repo`
3. Скопировать токен (один раз покажут)

Формат: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## 3. Окружение

```bash
cp .env.example .env
chmod 600 .env
# Если .env копировался с Windows — конвертировать в Unix:
sed -i 's/\r$//' .env
```

В `.env` обязательно заполнить:

```bash
GIT_PUSH_TOKEN=ghp_твой_токен
```

Остальное по желанию (пути, лимиты DNS, ветка и т.д.). См. [.env.example](.env.example).

---

## 3.1. DNS over TLS (по желанию)

Для резолва через зашифрованный DoT (например [NextDNS](https://nextdns.io)) в `.env` добавь:

```bash
DNS_OVER_TLS=1
DNS_OVER_TLS_SERVERS=45.90.28.61:твой-id.dns.nextdns.io,45.90.30.61:твой-id.dns.nextdns.io
```

Формат: через запятую пары `IP:hostname`. Без этих переменных используется обычный DNS (системный или `DNS_POOL`).

---

## 4. Входной файл

По умолчанию — `input.txt` в корне проекта. Либо в `.env` задать `INPUT_FILE=/path/to/domains.txt`.

---

## 5. Запуск

**Один прогон:**
```bash
docker compose run --rm app
```

**Фон с интервалом (production):**
```bash
# -d = detached (в фоне). В .env: SCHEDULE_INTERVAL_MINUTES=60
docker compose up -d daemon
```

**Без Docker:**
```bash
pip install -r requirements.txt
chmod +x run.sh sync.sh
./run.sh
```

Проверка без пуша (токен не подставлять):  
`docker compose run --rm -e GIT_PUSH_TOKEN= app`

---

## 6. Cron или daemon

```bash
crontab -e
```

**Вариант A — daemon (проще):** `docker compose up daemon` — работает в фоне. Частота в `.env`: `SCHEDULE_INTERVAL_MINUTES=60`.

**Вариант B — cron:**
```cron
0 3 * * * cd /path/to/DMTCDRK && docker compose run --rm app >> /var/log/dmtcdrk.log 2>&1
```

Без Docker:  
`0 3 * * * cd /path/to/DMTCDRK && ./run.sh >> /var/log/dmtcdrk.log 2>&1`

При изменении `output_optimized.txt` скрипт сделает commit и push.

---

## 7. Проверка

После первого запуска: `output_optimized.txt`, `.input_hash`. В конце вывода — строка `METRICS ...`.

---

## .gitignore

Не коммитятся: `.env`, `.env.*` (кроме `.env.example`), `*.tmp`, `domain_cache.json`, кэш тестов.  
`output_optimized.txt` и `.input_hash` коммитятся и пушатся скриптом.

---

## Production checklist

- [ ] `cp .env.example .env` и заполнить `GIT_PUSH_TOKEN`
- [ ] При NextDNS: `DNS_OVER_TLS=1` и `DNS_OVER_TLS_SERVERS=...`
- [ ] `./verify.sh` — проверка DNS и push с отладкой
- [ ] `input.txt` с доменами/IP в корне
- [ ] `docker compose up -d daemon` или `./deploy.sh`
- [ ] `docker compose logs -f daemon` — проверить логи
