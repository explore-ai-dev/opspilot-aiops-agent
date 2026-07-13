# Obsolete: the current demo-service runs directly on the Windows host with
# Python's standard library. This file is retained only as a record of the
# original containerized approach and is not referenced by docker-compose.yml.
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8000
CMD ["python", "app.py"]
