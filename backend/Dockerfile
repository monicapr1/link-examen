FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libz-dev libjpeg-dev && rm -rf /var/lib/apt/lists/*

RUN pip install flask redis requests flask-cors qrcode[pil]

COPY app.py .

CMD ["python", "app.py"]