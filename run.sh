#!/bin/sh

VENV_DIR=".venv"
SCRIPT="find_in_pdf_ocr.py"

# Проверка системных зависимостей
missing=""
command -v tesseract > /dev/null 2>&1 || missing="$missing tesseract"
command -v pdftotext > /dev/null 2>&1 || missing="$missing poppler"
command -v python3 > /dev/null 2>&1 || missing="$missing python3"

if [ -n "$missing" ]; then
    echo "[ERROR] Не установлены:$missing"
    echo "        brew install$missing"
    exit 1
fi

if ! tesseract --list-langs 2>/dev/null | grep -q rus; then
    echo "[ERROR] Нет русского языка для Tesseract"
    echo "        brew install tesseract-lang"
    exit 1
fi

# Python venv и зависимости
if [ ! -d "$VENV_DIR" ]; then
    echo "[SETUP] Создаю venv..."
    python3 -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/pip" show pdf2image pytesseract > /dev/null 2>&1; then
    echo "[SETUP] Устанавливаю зависимости..."
    "$VENV_DIR/bin/pip" install --quiet pdf2image pytesseract
fi

exec "$VENV_DIR/bin/python" -u "$SCRIPT" "$@"