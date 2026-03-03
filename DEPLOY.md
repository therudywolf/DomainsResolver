# Развёртывание на сервере

Краткая инструкция: скопировать проект на сервер, создать токен GitHub, создать `.env`, запускать по расписанию (cron + Docker или `run.sh`).

---

## 1. Копирование проекта на сервер

**Вариант A: клонирование репозитория**

```bash
git clone https://github.com/YOUR_USER/DMTCDRK.git
cd DMTCDRK
```

**Вариант B: архив**

На локальной машине: `git archive -o DMTCDRK.zip HEAD`, скопировать `DMTCDRK.zip` на сервер, распаковать и перейти в каталог.

---

## 2. Создание токена для Git push (GitHub)

Токен создаётся только в GitHub (или другом хосте), не в коде. Без него автоматический push не получится.

1. Зайти на https://github.com/settings/tokens
2. **Generate new token (classic)** или **Fine-grained**
3. Права: для classic — минимум `repo` (полный доступ к репозиторию)
4. Сгенерировать и **скопировать токен один раз** (потом его не покажут)

Пример вида токена: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## 3. Настройка окружения на сервере

В каталоге проекта:

```bash
cp .env.example .env
chmod 600 .env
```

Открыть `.env` и задать минимум:

```bash
# Обязательно для автоматического push (подставь свой токен)
GIT_PUSH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Ветка, в которую пушить (если не main — укажи)
# GIT_BRANCH=main
```

Остальные переменные опциональны (см. `.env.example`). Для экономии DNS можно оставить:

```bash
CONCURRENCY_LIMIT=1
DELAY=0.9
```

Файл `.env` в репозиторий не коммитится (уже в `.gitignore`).

---

## 4. Входной файл

Положить на сервер файл со списком доменов/IP/CIDR. По умолчанию ожидается имя `input.txt` в корне проекта:

```bash
# Пример
echo "example.com" >> input.txt
echo "192.168.1.0/24" >> input.txt
```

Или указать свой путь в `.env`:

```bash
INPUT_FILE=/path/on/server/domains.txt
```

---

## 5. Запуск

**Через Docker (рекомендуется)**

```bash
docker compose run --rm app ./run.sh
```

Проверка без push (только пайплайн):

```bash
docker compose run --rm -e GIT_PUSH_TOKEN= app ./run.sh
```

**Без Docker (голый Python)**

```bash
pip install -r requirements.txt
./run.sh
```

Убедиться, что `run.sh` и `sync.sh` исполняемые: `chmod +x run.sh sync.sh`.

---

## 6. Регулярный запуск (cron)

Раз в день в 3:00 (из каталога проекта):

```bash
crontab -e
```

Добавить строку (подставить путь к проекту):

```cron
0 3 * * * cd /path/to/DMTCDRK && docker compose run --rm app ./run.sh >> /var/log/dmtcdrk.log 2>&1
```

Без Docker:

```cron
0 3 * * * cd /path/to/DMTCDRK && ./run.sh >> /var/log/dmtcdrk.log 2>&1
```

Пайплайн выполнится только при изменении `input.txt` (сравнение по хешу). При изменении `output_optimized.txt` скрипт сделает commit и push.

---

## 7. Проверка

- После первого запуска в каталоге появятся `output_optimized.txt` и `.input_hash`.
- Логи — в stdout (и в файл, если перенаправление в cron задано).
- В конце прогона выводится строка `METRICS ...` с количеством доменов, IP и временем.

---

## 8. Что уже в .gitignore

В репозитории не попадут:

- `.env` и файлы вида `.env.*` (кроме `.env.example`)
- `.input_hash`
- временные файлы `*.tmp`, `output_optimized.txt.tmp`
- кэш pytest и прочее из стандартного .gitignore

Файл `output_optimized.txt` по умолчанию **коммитится** (его обновляет скрипт и пушит в репозиторий). Если нужно хранить его только на сервере — добавь `output_optimized.txt` в `.gitignore` и не используй автоматический push для этого файла.
