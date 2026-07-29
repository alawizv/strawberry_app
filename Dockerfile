FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3000

ENTRYPOINT ["streamlit", "run", "Dashboard.py", "--server.port=3000", "--server.address=0.0.0.0", "--server.headless=true"]
