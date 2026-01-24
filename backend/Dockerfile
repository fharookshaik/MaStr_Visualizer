FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run init script to populate DB if empty, then start the app
CMD ["sh", "-c", "python init_db.py && uvicorn app:app --host 0.0.0.0 --port 8000"]
