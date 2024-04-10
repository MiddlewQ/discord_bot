# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /usr/src/app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    ffmpeg \
    gcc \
    libffi-dev \
    libnacl-dev \
    python3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Pip complains about not using virtual environments
ENV PIP_ROOT_USER_ACTION=ignore

ENV PYTHONPATH /usr/src/app/src


# Upgrade pip before installing any Python packages
RUN pip install --upgrade pip

# Install any needed packages specified in requirements.txt
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


# Make port 80 available to the world outside this container
# (Useful if your bot has web server functionality, can be removed otherwise)
# EXPOSE 80

# Define environment variable
# (Ensure to use environment variables for sensitive data like bot tokens)
ENV NAME World

# Run main.py when the container launches
CMD ["python", "-m", "src.main"]
