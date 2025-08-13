# Use the official Python 3.12 slim image as the base (more stable and secure)
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements file separately for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files into the container
COPY . .

# Expose port 5000 for the application
EXPOSE 5000

# Command to run the app
CMD ["python", "launch.py"]
