# Use an official Python runtime as a parent image
FROM python:3.10-slim-bookworm

# Set the working directory in the container
WORKDIR /usr/src/app


RUN apt-get update && apt-get install -y --no-install-recommends \
     ffmpeg nodejs npm \
     && rm -rf /var/lib/apt/lists/*


# Upgrade pip before installing any Python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
RUN mkdir -p /usr/src/app/logs

# Run main.py when the container launches
CMD ["python", "-m", "src.main"]
