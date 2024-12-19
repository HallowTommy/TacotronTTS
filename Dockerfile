# Используем базовый образ Python
FROM python:3.9-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1-dev \
    librubberband-dev \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Установка рабочего каталога
WORKDIR /app

# Копирование приложения в контейнер
COPY . /app

# Установка виртуального окружения и зависимостей
RUN python -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

# Установка переменных окружения
ENV PATH="/opt/venv/bin:$PATH"

# Указание порта для приложения
EXPOSE 5000

# Команда для запуска приложения
CMD ["python", "app.py"]
