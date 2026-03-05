#!/usr/bin/env bash
# Проверка WireGuard в контейнере: туннель поднят, handshake свежий, резолв и трафик через WG.
set -e
cd "$(dirname "$0")"

echo "=============================================="
echo "  DMTCDRK — проверка WireGuard"
echo "=============================================="
echo ""

# Поднять wireguard если ещё не запущен
if ! docker compose ps wireguard 2>/dev/null | grep -q "Up"; then
  echo "[*] Запуск WireGuard..."
  docker compose up -d wireguard
  echo "[*] Ожидание поднятия туннеля (3 с)..."
  sleep 3
fi

# 1) Интерфейс и handshake
echo "[1/3] Интерфейс и handshake..."
if ! docker compose exec -T wireguard wg show 2>/dev/null; then
  echo "[ERROR] wg show не удался. Туннель не поднят?"
  exit 1
fi
if ! docker compose exec -T wireguard wg show 2>/dev/null | grep -q "latest handshake"; then
  echo "[WARN] Нет handshake (подожди несколько секунд и повтори)."
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
