# Базовый образ
FROM python:3.9-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1-dev \
    librubberband-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Установка виртуального окружения и зависимостей
WORKDIR /app
COPY . /app
RUN python -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -r requirements.txt

# Установка переменных окружения
ENV PATH="/opt/venv/bin:$PATH"

# Указание порта для Flask
EXPOSE 5000

# Команда для запуска приложения
CMD ["python", "app.py"]
