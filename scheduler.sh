#!/usr/bin/env bash
# Запускает run.sh каждые SCHEDULE_INTERVAL_MINUTES минут.
# Использование: docker compose up daemon

set -e
INTERVAL="${SCHEDULE_INTERVAL_MINUTES:-60}"
SCRIPT_DIR="${SCRIPT_DIR:-.}"

cd "$SCRIPT_DIR"

echo "[SCHEDULER] Запуск. Интервал проверки: ${INTERVAL} мин."
echo "[SCHEDULER] Первый прогон — сразу, далее каждые ${INTERVAL} мин."
echo ""

while true; do
  bash run.sh
  echo "[SCHEDULER] Следующий прогон через ${INTERVAL} мин. ($(date))"
  sleep "$((INTERVAL * 60))"
done
