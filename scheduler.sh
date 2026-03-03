#!/usr/bin/env bash
# Запускает run.sh каждые SCHEDULE_INTERVAL_MINUTES минут.
# Использование: docker compose up -d daemon

set -e
INTERVAL="${SCHEDULE_INTERVAL_MINUTES:-60}"
SCRIPT_DIR="${SCRIPT_DIR:-.}"

cd "$SCRIPT_DIR"

echo "[SCHEDULER] Интервал: ${INTERVAL} мин. DELAY=${DELAY:-1.0}s"
echo "[SCHEDULER] Первый прогон — сразу"
echo ""

while true; do
  echo "[SCHEDULER] Прогон $(date '+%Y-%m-%d %H:%M')"
  bash run.sh
  echo "[SCHEDULER] Следующий через ${INTERVAL} мин."
  sleep "$((INTERVAL * 60))"
done
