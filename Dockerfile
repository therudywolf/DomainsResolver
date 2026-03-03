# Pipeline: resolve domains -> IP/CIDR, optimize, output to file.
# Use with: docker compose run --rm app ./run.sh
FROM python:3.11-slim
RUN pip install --no-cache-dir dnspython
WORKDIR /data
COPY requirements.txt pipeline.py script.py run.sh sync.sh ./
RUN chmod +x run.sh sync.sh
CMD ["./run.sh"]
