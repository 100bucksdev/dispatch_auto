FROM python:3.12-slim

WORKDIR /app

# Устанавливаем системные зависимости, необходимые для Playwright и xvfb
RUN apt-get update && apt-get install -y \
    gcc \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    xvfb \
    libxcursor1 \
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
    libpangocairo-1.0-0 \
    libcairo-gobject2 \
    libgstreamer1.0-0 \
    libgtk-4-1 \
    libgraphene-1.0-0 \
    libxslt1.1 \
    libwoff1 \
    libvpx7 \
    libevent-2.1-7 \
    libopus0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    libflite1 \
    libwebpdemux2 \
    libharfbuzz-icu0 \
    libwebpmux3 \
    libenchant-2-2 \
    libsecret-1-0 \
    libhyphen0 \
    libmanette-0.2-0 \
    libpsl5 \
    libnghttp2-14 \
    libgles2 \
    libx264-164 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN pip install playwright && playwright install

COPY . .

ENV PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PORT=6000

EXPOSE 6000