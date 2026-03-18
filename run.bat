@echo off

set VENV_DIR=.venv
set SCRIPT=find_in_pdf_ocr.py

:: Проверка системных зависимостей
where tesseract >nul 2>&1 || (
    echo [ERROR] Не установлен tesseract
    echo         Установите: https://github.com/UB-Mannheim/tesseract/wiki
    exit /b 1
)

where python >nul 2>&1 || (
    echo [ERROR] Не установлен python
    exit /b 1
)

tesseract --list-langs 2>nul | findstr /i "rus" >nul || (
    echo [ERROR] Нет русского языка для Tesseract
    echo         Переустановите tesseract с русским языком
    exit /b 1
)

:: Python venv и зависимости
if not exist "%VENV_DIR%" (
    echo [SETUP] Создаю venv...
    python -m venv "%VENV_DIR%"
)

"%VENV_DIR%\Scripts\pip" show pdf2image pytesseract >nul 2>&1 || (
    echo [SETUP] Устанавливаю зависимости...
    "%VENV_DIR%\Scripts\pip" install --quiet pdf2image pytesseract
)

"%VENV_DIR%\Scripts\python" -u "%SCRIPT%" %*