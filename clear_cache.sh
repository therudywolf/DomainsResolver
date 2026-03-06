#!/usr/bin/env bash
# DMTCDRK — полная очистка кэша и служебных флагов.
# После запуска следующий прогон будет считать все домены новыми (полный резолв).
# Запуск: ./clear_cache.sh

set -e
cd "$(dirname "$0")"

echo ""
echo "  DMTCDRK — очистка кэша"
echo "  ======================"
echo ""

# Имя файла кэша доменов (из .env или по умолчанию)
CACHE_FILE="domain_cache.json"
[ -f .env ] && . ./.env 2>/dev/null || true
CACHE_FILE="${DOMAIN_CACHE_FILE:-domain_cache.json}"

removed=0

# Кэш доменов (incremental mode)
for f in "$CACHE_FILE" "${CACHE_FILE}.tmp"; do
  if [ -f "$f" ]; then
    rm -f "$f"
    echo "[OK] Удалён: $f"
    removed=$((removed + 1))
  fi
done

# Хеш входа (чтобы следующий run не пропустил пайплайн)
if [ -f .input_hash ]; then
  rm -f .input_hash
  echo "[OK] Удалён: .input_hash"
  removed=$((removed + 1))
fi

# Хеш для verify
if [ -f .verify_hash ]; then
  rm -f .verify_hash
  echo "[OK] Удалён: .verify_hash"
  removed=$((removed + 1))
fi

# Флаг «первый запуск выполнен» (при следующем start.sh снова пройдёт verify)
if [ -f .start_done ]; then
  rm -f .start_done
  echo "[OK] Удалён: .start_done"
  removed=$((removed + 1))
fi

if [ "$removed" -eq 0 ]; then
  echo "[*] Нечего удалять — кэш уже пуст."
else
  echo ""
  echo "  Удалено файлов: $removed"
  echo "  Следующий прогон/start.sh выполнит полный резолв (без кэша)."
fi

echo ""
