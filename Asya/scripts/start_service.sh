#!/bin/bash

# ===============================================
# start_service.sh — Запуск сервиса "Ася"
# Нейрозвонилка на базе FastAPI + NeMo + ARI
# ===============================================

set -e  # Прервать при любой ошибке

PROJECT_DIR="/opt/asya_ari_mvp"  # ← УКАЖИТЕ ПУТЬ К ВАШЕМУ ПРОЕКТУ
SRC_DIR="$PROJECT_DIR/src"
LOG_DIR="$PROJECT_DIR/logs"
PID_FILE="$LOG_DIR/asya.pid"

# Создаём директории, если их нет
mkdir -p "$LOG_DIR"

echo "🚀 Запуск сервиса 'Ася'..."

# Проверяем, что проект существует
if [ ! -d "$PROJECT_DIR" ]; then
  echo "❌ ОШИБКА: Проект не найден по пути: $PROJECT_DIR"
  echo "   Убедитесь, что проект распакован в /opt/asya_ari_mvp"
  exit 1
fi

# Проверяем наличие requirements.txt
if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
  echo "❌ ОШИБКА: requirements.txt не найден!"
  exit 1
fi

# Проверяем, что FastAPI приложение существует
if [ ! -f "$SRC_DIR/api/main.py" ]; then
  echo "❌ ОШИБКА: main.py не найден в $SRC_DIR/api/"
  exit 1
fi

# Загружаем переменные окружения из .env (если есть)
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
  echo "🔧 Загрузка переменных окружения из .env..."
  export $(grep -v '^#' "$ENV_FILE" | xargs)
else
  echo "⚠️  .env файл не найден. Используются значения по умолчанию."
fi

# Проверяем, что ARI-пароль задан
if [ -z "$ARI_PASSWORD" ]; then
  echo "❌ ОШИБКА: Переменная ARI_PASSWORD не установлена!"
  echo "   Создайте файл .env в корне проекта:"
  echo "   ARI_USERNAME=asya_app"
  echo "   ARI_PASSWORD=your_secure_password_here"
  exit 1
fi

# Проверяем, что Python и pip установлены
if ! command -v python3 &> /dev/null; then
  echo "❌ Python 3 не установлен!"
  exit 1
fi

# Проверяем, установлены ли зависимости
if [ ! -d "$PROJECT_DIR/venv" ]; then
  echo "📦 Установка виртуального окружения..."
  python3 -m venv "$PROJECT_DIR/venv"
fi

source "$PROJECT_DIR/venv/bin/activate"

# Устанавливаем зависимости (если ещё не установлены)
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt" || {
  echo "❌ Не удалось установить зависимости!"
  exit 1
}

# Проверяем, что сервер не запущен
if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
  echo "🛑 Сервис уже запущен (PID: $(cat "$PID_FILE"))"
  echo "   Остановите его командой: ./stop_service.sh"
  exit 1
fi

# Запускаем FastAPI в фоне
echo "▶️  Запуск FastAPI-сервера на http://0.0.0.0:8000..."
uvicorn \
  --host 0.0.0.0 \
  --port 8000 \
  --reload=false \
  --log-level info \
  --workers 2 \
  "$SRC_DIR/api/main:app" \
  >> "$LOG_DIR/asya.log" 2>&1 &

# Сохраняем PID
echo $! > "$PID_FILE"

echo "✅ Сервис 'Ася' запущен!"
echo "   PID: $(cat "$PID_FILE")"
echo "   Логи: tail -f $LOG_DIR/asya.log"
echo "   Проверка статуса: curl http://localhost:8000/health"