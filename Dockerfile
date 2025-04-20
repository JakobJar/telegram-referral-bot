FROM python:3.13-slim

# Create a non-root user
RUN useradd -m -s /bin/bash appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Change ownership of the /app directory to appuser
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

CMD ["python", "main.py"]