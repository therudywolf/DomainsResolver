# Развёртывание (Debian 12)

Одна команда: `./start.sh`

---

## Быстрый старт

```bash
git clone https://github.com/rudywolf/DMTCDRK.git
cd DMTCDRK
chmod +x start.sh verify.sh deploy.sh
./start.sh
```

`start.sh` сам:
- создаёт `.env` и `input.txt` из примеров (если нет)
- исправляет CRLF в `.env`
- собирает образ
- при первом запуске проверяет DNS и push
- запускает daemon в фоне

Заполни `GIT_PUSH_TOKEN` в `.env`, добавь домены в `input.txt`.

---

## Требования

- Docker + docker compose v2
- Debian 12: `apt install docker.io docker-compose-v2`

---

## Команды

| Команда | Описание |
|---------|----------|
| `./start.sh` | Подготовка + проверка + daemon |
| `./verify.sh` | Только проверка |
| `docker compose --profile run run --rm run` | Один прогон (cron) |
| `docker compose up -d daemon` | Фон |
| `docker compose logs -f daemon` | Логи |

---

## .env

Обязательно: `GIT_PUSH_TOKEN`  
При NextDNS: `DNS_OVER_TLS=1` и `DNS_OVER_TLS_SERVERS=...`

Если `.env` копировался с Windows: `sed -i 's/\r$//' .env`

---

## Production checklist

- [ ] `./start.sh` или заполнить `.env` и `input.txt` вручную
- [ ] `GIT_PUSH_TOKEN` в `.env`
- [ ] `input.txt` с доменами
- [ ] `docker compose logs -f daemon` — проверить логи
