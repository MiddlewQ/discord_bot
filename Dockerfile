# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm

# Set the working directory in the container
WORKDIR /usr/src/app

# Update 
RUN apt-get update && apt-get install -y --no-install-recommends \
     ffmpeg curl ca-certificates unzip \
     && rm -rf /var/lib/apt/lists/*

# Install Deno (yt-dlp JS runtime)
ENV DENO_INSTALL=/root/.deno
ENV PATH="${DENO_INSTALL}/bin:${PATH}"
RUN curl -fsSL https://deno.land/install.sh | sh

# Upgrade pip before installing any Python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
RUN mkdir -p /usr/src/app/logs

# Update yt-dlp on every start, since YouTube changes often break older versions; then run main.py
# exec makes python PID 1, so it receives Docker's stop signal (SIGTERM) instead of sh swallowing it
CMD ["sh", "-c", "pip install --no-cache-dir -U 'yt-dlp[default]' && exec python -m src.main"]
