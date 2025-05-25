# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the src directory into the container at /app/src
COPY ./src ./src

# Copy the data directory (for input json)
COPY ./data ./data

# Make data directory writable for output (if script writes there directly, though better to mount volumes)
# RUN mkdir -p /app/data && chmod -R 777 /app/data

# Command to run the application
# This will be overridden by docker-compose for the parser service,
# but good to have a default.
# CMD ["python", "src/main.py"]
ENTRYPOINT ["python", "src/main.py"]
