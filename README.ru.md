# pdf-text-finder

Поиск текста в PDF-файлах через OCR (Tesseract). Полезно для сканированных документов без текстового слоя.

[English documentation](README.md)

## Возможности

- OCR-распознавание PDF через Tesseract (русский язык)
- Параллельная обработка на всех ядрах CPU
- Кеширование результатов OCR — повторный поиск мгновенный
- Постраничный вывод совпадений
- Копирование найденных файлов в `output/`

## Системные зависимости

### macOS
```bash
brew install tesseract tesseract-lang poppler
```

### Windows
- [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) (с русским языком)
- [Poppler](https://github.com/oschwartz10612/poppler-windows/releases)
- Python 3

## Использование

### macOS / Linux
```bash
./run.sh <запрос>              # поиск
./run.sh <запрос> --copy       # поиск + копирование в output/
./run.sh <запрос> source/папка # поиск в конкретной папке
```

### Windows
```cmd
run.bat <запрос>
run.bat <запрос> --copy
```

По умолчанию PDF-файлы ищутся в папке `source/` относительно корня проекта. Положите туда свои файлы перед запуском.

При первом запуске автоматически создаётся venv и устанавливаются Python-зависимости.

## Как это работает

1. PDF конвертируется в изображения (poppler)
2. Каждая страница распознаётся через Tesseract OCR
3. Результат OCR кешируется в `ocr_cache.json` (по MD5 хешу файла)
4. При повторном запуске используется кеш — OCR не повторяется