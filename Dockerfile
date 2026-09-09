FROM python:3.11-slim

WORKDIR /app

COPY frontend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/ ./agent/
COPY frontend/ ./frontend/

WORKDIR /app/frontend
EXPOSE 8080

CMD ["sh", "-c", "streamlit run app.py --server.port=8080 --server.address=0.0.0.0 --server.headless=true"]
