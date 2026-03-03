# DMTCDRK — Domain-to-IP/CIDR pipeline

Reads a single input file (`input.txt`) containing domains (including wildcards like `*.domain.com`), raw IPs, and CIDR subnets. Resolves domains to IPv4 via async DNS, merges with existing IP/CIDR, optimizes the list (dedup, aggregate subnets), and writes the result to `output_optimized.txt`. Optional Git push when output changes.

- **Run by change**: Hash of `input.txt` is stored in `.input_hash`; pipeline runs only when the input file changes (e.g. cron daily).
- **DNS-friendly**: Configurable concurrency, delay, resolver timeout, and backoff on repeated failures.
- **Docker**: One service, run via `docker compose run --rm app ./run.sh`.

## Requirements

- Python 3.10+
- [dnspython](https://pypi.org/project/dnspython/) (`pip install -r requirements.txt`)
- Optional: Docker and Docker Compose for containerized runs

## Quick start

1. Create `input.txt` in the project root: one entry per line (domain, `*.domain.com`, IP, or CIDR). Empty lines and lines starting with `#` are ignored.

2. **Local run**
   ```bash
   pip install -r requirements.txt
   python pipeline.py              # single run
   ./run.sh                        # run with hash check + optional git push
   ```

3. **Docker**
   ```bash
   docker compose run --rm app ./run.sh
   ```
   The service uses the `daily` profile so it does not start with `docker compose up`; use `run` for one-off or cron.

4. **Cron (e.g. daily at 3:00)**  
   From repo directory:
   ```bash
   0 3 * * * cd /path/to/DMTCDRK && docker compose run --rm app ./run.sh
   ```
   Or without Docker: `0 3 * * * cd /path/to/DMTCDRK && ./run.sh`

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `INPUT_FILE` | `input.txt` | Path to input file (domains + IP/CIDR). |
| `OUTPUT_FILE` | `output_optimized.txt` | Path to output file. |
| `HASH_FILE` | `.input_hash` | File storing hash of input for change detection. |
| `CONCURRENCY_LIMIT` | `1` | Max concurrent DNS queries (keep low to avoid rate limits). |
| `DELAY` | `0.9` | Delay in seconds between DNS requests. |
| `RESOLVER_TIMEOUT` | `5.0` | DNS resolver timeout in seconds. |
| `DNS_POOL` | (built-in list) | Comma-separated list of DNS servers (e.g. `8.8.8.8,1.1.1.1`). |
| `KEEP_LAST_OUTPUT_IF_EMPTY` | — | Set to `1`/`true`/`yes` to keep previous output when optimized list is empty. |
| `FORCE_RUN` | — | Set to `1`/`true`/`yes` to skip hash check and always run pipeline. |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `GIT_PUSH_TOKEN` | — | HTTPS token for `git push` (e.g. GitHub PAT). Origin URL is restored after push. |
| `GIT_BRANCH` | (current branch) | Branch to push to (e.g. `main`). |
| `GIT_SIGN_COMMITS` | — | Set to `1`/`true` to sign commits with GPG (`-S`). |
| `GIT_PUSH_RETRIES` | `3` | Number of retries for `git push`. |
| `GIT_PUSH_SLEEP` | `5` | Seconds to wait between push retries. |
| `RESOLVE_AAAA` | — | Set to `1`/`true`/`yes` to also resolve IPv6 (AAAA) and append to output. |

## Git push without password

- **HTTPS**: Set `GIT_PUSH_TOKEN` in `.env` (copy from `.env.example`). `sync.sh` will use it for push and then restore the original `origin` URL.
- **SSH**: Use a deploy key; ensure the container or host has the key and `git push` works without a password. Do not set `GIT_PUSH_TOKEN`.

## Modes

- **Normal**: `./run.sh` or `python pipeline.py` — full pipeline (read → resolve → optimize → write). Run script also updates `.input_hash` and runs `sync.sh` when output or hash changed.
- **Dry-run**: `python pipeline.py --dry-run` — only read and classify input, print counts; no DNS, no write.
- **Force run**: `FORCE_RUN=1 ./run.sh` — ignore input hash and run pipeline anyway.

## Output

- **output_optimized.txt**: One IP or CIDR per line, sorted. Written atomically (via `.tmp` + rename).
- **METRICS**: One line at the end of a successful run, e.g.  
  `METRICS domains_in=100 domains_ok=95 domains_fail=5 ips_resolved=200 ips_cidr_input=50 optimized_entries=220 duration_sec=120`

## Limitations

- IPv4 only by default; set `RESOLVE_AAAA=1` to include IPv6 (AAAA) in the output (appended after optimized IPv4).
- With `KEEP_LAST_OUTPUT_IF_EMPTY=1`, an empty optimized list does not overwrite the previous file.

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Project layout

- `pipeline.py` — main pipeline (read, classify, resolve, optimize, write).
- `ip_utils.py` — IP/CIDR parsing and `optimize_list`.
- `script.py` — standalone consolidator (scans directory, uses `ip_utils`).
- `run.sh` — hash check, run pipeline, update hash, call `sync.sh`.
- `sync.sh` — git add/commit/push when output or hash changed; retries and restores origin.
