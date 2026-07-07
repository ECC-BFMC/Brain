FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        libgl1 \
        libglib2.0-0 \
        libssl-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5005

CMD ["python", "main.py", "--dev"]
