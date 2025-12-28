# Use an official Python runtime as a parent image
FROM python:3.10-slim-bookworm

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

# Run main.py when the container launches
CMD ["python", "-m", "src.main"]
