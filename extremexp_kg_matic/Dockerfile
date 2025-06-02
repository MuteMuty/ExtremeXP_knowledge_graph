# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the src directory into the container at /app/src
COPY ./src ./src

# Create data directory
RUN mkdir -p /app/data

# Command to run the application
ENTRYPOINT ["python", "src/main.py"]
