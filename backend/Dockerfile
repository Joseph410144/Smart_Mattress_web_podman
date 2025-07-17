# FROM python:3.10-slim

# WORKDIR /app

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

# EXPOSE 8001
# EXPOSE 8000
# EXPOSE 5001

# CMD ["python", "app.py"]
# CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
# CMD ["uvicorn", "app_download_static:app", "--host", "0.0.0.0", "--port", "8001"]

FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
EXPOSE 8001
EXPOSE 5001

ENTRYPOINT ["/entrypoint.sh"]
CMD ["app", "8000"]
