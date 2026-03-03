# Развёртывание на сервере

Кратко: скопировать проект → создать токен GitHub → заполнить `.env` → запускать по cron.

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
```

В `.env` обязательно заполнить:

```bash
GIT_PUSH_TOKEN=ghp_твой_токен
```

Остальное по желанию (пути, лимиты DNS, ветка и т.д.). См. [.env.example](.env.example).

---

## 4. Входной файл

По умолчанию — `input.txt` в корне проекта. Либо в `.env` задать `INPUT_FILE=/path/to/domains.txt`.

---

## 5. Запуск

**Docker:**

```bash
docker compose run --rm app ./run.sh
```

**Без Docker:**

```bash
pip install -r requirements.txt
chmod +x run.sh sync.sh
./run.sh
```

Проверка без пуша (токен не подставлять):  
`docker compose run --rm -e GIT_PUSH_TOKEN= app ./run.sh`

---

## 6. Cron (раз в день)

```bash
crontab -e
```

Строка (подставить путь):

```cron
0 3 * * * cd /path/to/DMTCDRK && docker compose run --rm app ./run.sh >> /var/log/dmtcdrk.log 2>&1
```

Без Docker:  
`0 3 * * * cd /path/to/DMTCDRK && ./run.sh >> /var/log/dmtcdrk.log 2>&1`

Пайплайн выполняется только при изменении `input.txt`. При изменении `output_optimized.txt` скрипт сделает commit и push.

---

## 7. Проверка

После первого запуска: `output_optimized.txt`, `.input_hash`. В конце вывода — строка `METRICS ...`.

---

## .gitignore

Не коммитятся: `.env`, `.env.*` (кроме `.env.example`), `*.tmp`, `output_optimized.txt.tmp`, кэш тестов.  
`output_optimized.txt` и `.input_hash` коммитятся и пушатся скриптом.
