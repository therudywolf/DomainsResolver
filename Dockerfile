# DMTCDRK — Debian 12 compatible
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends git \
  && rm -rf /var/lib/apt/lists/* \
  && pip install --no-cache-dir dnspython

RUN adduser --disabled-password --gecos "" pipeline

WORKDIR /data
COPY requirements.txt pipeline.py script.py ip_utils.py \
  run.sh sync.sh scheduler.sh verify_inner.sh verify_input.txt ./
RUN chmod +x run.sh sync.sh scheduler.sh verify_inner.sh \
  && chown -R pipeline:pipeline /data

USER pipeline

CMD ["./run.sh"]
