FROM python:3.10-slim

# Set work directory
WORKDIR /app

# Copy application files (excluding those in .dockerignore)
COPY database.py .
COPY server_torque.py .
COPY templates/ templates/
COPY reader/ reader/

# Expose server port
EXPOSE 8080

# Run the Torque server
CMD ["python", "server_torque.py"]
