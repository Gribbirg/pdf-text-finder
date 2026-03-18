  #!/bin/sh

SEARCH_TERM="Грибков"
SOURCE_DIR="source"
PARALLEL=8

export SEARCH_TERM

search_file() {
    pdf="$1"
    # Этап 1: быстрая проверка всего файла
    if ! pdftotext "$pdf" - 2>/dev/null | grep -qi "$SEARCH_TERM"; then
        return
    fi
    # Этап 2: постраничный поиск только если найдено
    page=1
    while true; do
        text=$(pdftotext -f "$page" -l "$page" "$pdf" - 2>/dev/null)
        [ -z "$text" ] && break
        if echo "$text" | grep -qi "$SEARCH_TERM"; then
            echo "[НАЙДЕНО] $pdf — стр. $page"
        fi
        page=$((page + 1))
    done
}

export -f search_file

start=$(date +%s)

total=$(find "$SOURCE_DIR" -name "*.pdf" -type f | wc -l | tr -d ' ')
echo "Файлов PDF: $total"
echo "Параллельных потоков: $PARALLEL"
echo "Поиск: \"$SEARCH_TERM\""
echo "---"

find "$SOURCE_DIR" -name "*.pdf" -type f | xargs -P "$PARALLEL" -I {} sh -c 'search_file "$@"' _ {}

end=$(date +%s)
elapsed=$((end - start))
echo ""
echo "--- Итого ---"
echo "Файлов: $total"
echo "Время: ${elapsed}с"
if [ "$elapsed" -gt 0 ]; then
    echo "Скорость: $((total / elapsed)) файлов/с"
fi
