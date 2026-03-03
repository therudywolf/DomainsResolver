#!/usr/bin/env bash
# Проверка через Docker Compose
cd "$(dirname "$0")"
[ ! -f .env ] && cp .env.example .env
[ -f .env ] && sed -i 's/\r$//' .env 2>/dev/null || true
docker compose build -q
docker compose --profile verify run --rm verify
