FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Luo hakemisto tietokannalle
RUN mkdir -p /app/data

ENV DATABASE_URL=sqlite:////app/data/cot_data.db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
