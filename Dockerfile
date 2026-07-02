FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py giflet_core.py web_app.py ./
COPY web ./web

EXPOSE 8765

CMD ["python", "web_app.py", "--host", "0.0.0.0", "--port", "8765", "--no-open"]
