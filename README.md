# pdf-text-finder

Search text in PDF files using OCR (Tesseract). Useful for scanned documents without a text layer.

[Документация на русском](README.ru.md)

## Features

- OCR recognition via Tesseract (Russian language)
- Parallel processing on all CPU cores
- OCR result caching — repeated searches are instant
- Per-page match output
- Copy matched files to `output/`

## System dependencies

### macOS
```bash
brew install tesseract tesseract-lang poppler
```

### Windows
- [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) (with Russian language)
- [Poppler](https://github.com/oschwartz10612/poppler-windows/releases)
- Python 3

## Usage

### macOS / Linux
```bash
./run.sh <query>              # search
./run.sh <query> --copy       # search + copy results to output/
./run.sh <query> source/sub   # search in a specific folder
```

### Windows
```cmd
run.bat <query>
run.bat <query> --copy
```

By default, PDF files are searched in the `source/` directory relative to the project root.

On first run, a Python venv is automatically created and dependencies are installed.

## How it works

1. PDF is converted to images (poppler)
2. Each page is recognized via Tesseract OCR
3. OCR results are cached in `ocr_cache.json` (keyed by file MD5 hash)
4. On subsequent runs, cached results are used — no repeated OCR