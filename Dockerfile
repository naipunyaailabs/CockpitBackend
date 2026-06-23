FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code and the p directory containing the database json
COPY backend/ ./backend/
COPY p/ ./p/

WORKDIR /app/backend

EXPOSE 8005

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005"]
