FROM python:3.12-slim

# Set metadata
LABEL maintainer="Harness Workspace Plugin"
LABEL description="Harness Workspace Preparation Plugin for CI/CD pipeline automation"
LABEL version="1.0.0"

# Copy application code to the expected location
COPY main.py /usr/local/bin/plugin.py

# Set environment variables for better Python behavior
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Use the specified entrypoint
ENTRYPOINT python /usr/local/bin/plugin.py