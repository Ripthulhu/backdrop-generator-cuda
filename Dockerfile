FROM jrottenberg/ffmpeg:7.0-nvidia

# 1. Lightweight Python runtime (Debian 12 gives Python 3.11)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv && \
    rm -rf /var/lib/apt/lists/*

ENV PIP_BREAK_SYSTEM_PACKAGES=1

# 2. Optional: keep the CLI name `python`
RUN ln -s /usr/bin/python3 /usr/local/bin/python

# 3. Your application
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt

# 4. Entrypoint that turns env-vars  ^f^r CLI flags
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
