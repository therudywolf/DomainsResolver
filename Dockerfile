# Pipeline: resolve domains -> IP/CIDR, optimize, output to file.
# Use with: docker compose run --rm app ./run.sh
FROM python:3.11-slim
LABEL org.opencontainers.image.description="DMTCDRK pipeline: resolve domains to IP/CIDR and optimize list"

RUN pip install --no-cache-dir dnspython

# Run as non-root user
RUN adduser --disabled-password --gecos "" pipeline

WORKDIR /data
COPY requirements.txt pipeline.py script.py ip_utils.py run.sh sync.sh ./
RUN chmod +x run.sh sync.sh && chown -R pipeline:pipeline /data

USER pipeline

HEALTHCHECK --interval=60s --timeout=5s --start-period=0s --retries=1 \
  CMD python3 -c "import ip_utils; print('ok')" || exit 1

CMD ["./run.sh"]
