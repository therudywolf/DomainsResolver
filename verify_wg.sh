#!/usr/bin/env bash
# Проверка WireGuard в контейнере: туннель поднят, handshake свежий, резолв и трафик через WG.
set -e
cd "$(dirname "$0")"

echo "=============================================="
echo "  DMTCDRK — проверка WireGuard"
echo "=============================================="
echo ""

# Конфиг WG (из .env или по умолчанию)
[ -f .env ] && set -a && . ./.env 2>/dev/null && set +a || true
WG_CONF="${WG_CONF:-forestserver_DE-DE-578.conf}"
if [ ! -f "wg/${WG_CONF}" ] && [ ! -f "wg/${WG_CONF%.conf}.conf" ]; then
  echo "[ERROR] Конфиг WG не найден: wg/${WG_CONF}"
  echo "        Положи конфиг в wg/ (например wg/forestserver_DE-DE-578.conf)."
  exit 1
fi

# Поднять wireguard если ещё не запущен
if ! docker compose ps wireguard 2>/dev/null | grep -q "Up"; then
  echo "[*] Запуск WireGuard..."
  docker compose up -d wireguard
  echo "[*] Ждём старта контейнера (2 с)..."
  sleep 2
  if ! docker compose ps wireguard 2>/dev/null | grep -q "Up"; then
    echo "[ERROR] Контейнер wireguard не запущен (возможно, упал при старте)."
    echo "[*] Логи:"
    docker compose logs --tail=50 wireguard 2>/dev/null || true
    echo ""
    echo "Подсказка: запускай без sudo — ./verify_wg.sh (если пользователь в группе docker)."
    exit 1
  fi
  echo "[*] Ожидание handshake (до 15 с)..."
  for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    if docker compose exec -T wireguard wg show 2>/dev/null | grep -q "latest handshake"; then
      echo "[*] Туннель поднят."
      break
    fi
    if [ "$i" -eq 15 ]; then
      echo "[ERROR] Handshake не получен за 15 с."
      echo "[*] Логи контейнера wireguard:"
      docker compose logs --tail=30 wireguard 2>/dev/null || true
      exit 1
    fi
    sleep 1
  done
  echo ""
fi

# 1) Интерфейс и handshake
echo "[1/3] Интерфейс и handshake..."
if ! docker compose exec -T wireguard wg show 2>/dev/null; then
  echo "[ERROR] wg show не удался. Туннель не поднят?"
  exit 1
fi
if ! docker compose exec -T wireguard wg show 2>/dev/null | grep -q "latest handshake"; then
  echo "[WARN] Нет handshake (подожди несколько секунд и повтори: ./verify_wg.sh)."
fi
echo ""

# 2) Резолв и трафик через WG (контейнер в сети wireguard)
echo "[2/3] Резолв и внешний IP через WG..."
if ! docker compose --profile verify_wg run --rm verify_wg; then
  echo "[ERROR] Проверка резолва/трафика не прошла."
  exit 1
fi
echo ""

echo "=============================================="
echo "  WireGuard работает."
echo "=============================================="
