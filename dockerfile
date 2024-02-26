# Base image
FROM python:3.9-slim

# Install git, necessary for any git dependencies in requirements.txt
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV HOST=0.0.0.0 \
    LISTEN_PORT=8000 \
    PYTHONUNBUFFERED=1

# Expose port 8000 for the application
EXPOSE 8000

# Set the working directory in the container
WORKDIR /chainlit-gcp

# Copy the Python dependencies file to the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the relevant directories and files to the container
COPY .chainlit .chainlit/
COPY db db/
COPY public public/
COPY app.py .
COPY vision.json .
COPY chainlit.md .

# If you have other configurations or scripts, copy them as well
# COPY config.yaml .
# COPY start.sh .

CMD ["chainlit", "run", "app.py"]