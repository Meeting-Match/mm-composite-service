# Use the official Python image from Docker Hub
FROM python:3.11-slim

# Set the working directory to mm-user-auth-service
WORKDIR /mm-composite-service

# Install system dependencies for mysqlclient
RUN apt-get update && apt-get install -y \
    pkg-config \
    libmariadb-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements.txt file to the working directory
COPY requirements.txt .

# Install the dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the working directory
COPY . .

# Set environment variables for Django
ENV DJANGO_SETTINGS_MODULE=mm_composite.settings
ENV PYTHONUNBUFFERED=1

# Expose Django port (8000)
EXPOSE 8000

# Run Django migrations and start the application
CMD ["sh", "-c", "python ./mm_composite/manage.py migrate && python ./mm_composite/manage.py runserver 0.0.0.0:8000"]
