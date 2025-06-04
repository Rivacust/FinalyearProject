# Use official Python 3.9 image
FROM python:3.9-slim

# Set environment vars
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential cmake \
    libboost-all-dev \
    libglib2.0-0 libsm6 libxrender1 libxext6 \
    && apt-get clean

# Create working directory
WORKDIR /app

# Copy files
COPY . /app/

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Collect static (if needed)
RUN python manage.py collectstatic --noinput || true

# Run Django server
CMD ["gunicorn", "FinalyearProject.wsgi:application", "--bind", "0.0.0.0:8000"]
