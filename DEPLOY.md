# Развёртывание (Debian 12)

Одна команда: `./start.sh`

---

## Быстрый старт

```bash
git clone https://github.com/rudywolf/DMTCDRK.git
cd DMTCDRK
chmod +x start.sh verify.sh verify_wg.sh deploy.sh
./start.sh
```

`start.sh` сам:
- создаёт `.env` и `input.txt` из примеров (если нет)
- исправляет CRLF в `.env`
- собирает образы (в т.ч. WireGuard)
- поднимает контейнер WireGuard по конфигу `wg/forestserver_DE-DE-578.conf`
- при первом запуске проверяет DNS и push (резолв через WG)
- запускает daemon в фоне

Заполни `GIT_PUSH_TOKEN` в `.env`, добавь домены в `input.txt`. Конфиг WG должен лежать в `wg/forestserver_DE-DE-578.conf`.

---

## Требования

- Docker + docker compose v2
- Debian 12: `apt install docker.io docker-compose-v2`

---

## Команды

| Команда | Описание |
|---------|----------|
| `./start.sh` | Подготовка + WireGuard + проверка + daemon |
| `./verify.sh` | Только проверка (DNS + push) |
| `./verify_wg.sh` | Проверка WireGuard: туннель, handshake, резолв и трафик через WG |
| `docker compose --profile run run --rm run` | Один прогон (cron) |
| `docker compose up -d daemon` | Фон |
| `docker compose logs -f daemon` | Логи |

**WireGuard:** конфиг `wg/forestserver_DE-DE-578.conf`. Резолв доменов только через DNS этого WG (10.2.0.1). Verify/run/daemon работают в сети контейнера WG.

---

## .env

Обязательно: `GIT_PUSH_TOKEN`, `GIT_USER_NAME`, `GIT_USER_EMAIL`  
Резолв доменов идёт через DNS из конфига WG (/etc/resolv.conf в контейнере). Доп. переменные для DNS не нужны.

**Скорость:** `DELAY=1.0` и `CONCURRENCY_LIMIT=1` — по умолчанию. Быстрее = риск бана.

Если `.env` копировался с Windows: `sed -i 's/\r$//' .env`

---

## Production checklist

- [ ] `./start.sh` или заполнить `.env` и `input.txt` вручную
- [ ] `GIT_PUSH_TOKEN` в `.env`
- [ ] Конфиг WG в `wg/forestserver_DE-DE-578.conf`
- [ ] `input.txt` с доменами
- [ ] `./verify_wg.sh` — убедиться, что WG поднят и резолв через него
- [ ] `docker compose logs -f daemon` — проверить логи
