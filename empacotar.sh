#!/usr/bin/env bash
# Gera o arquivo de entrega: código + relatório + README + link do vídeo + resultados.
set -e
cd "$(dirname "$0")"
OUT=viniciusarantes_marianarufo.zip
rm -f "$OUT"
zip -qr "$OUT" README.md requirements.txt .env.example main.py link_video.txt roteiro_video.md empacotar.sh \
    othello agent players ui experiments tests results relatorio/relatorio.pdf relatorio/relatorio.md \
    relatorio/build.py relatorio/style.css relatorio/resultados.md relatorio/conclusao.md \
    -x "*/__pycache__/*" "*.pyc"
[ -f slides.pdf ] && zip -q "$OUT" slides.pdf && echo "slides.pdf incluído"
echo "OK: $OUT ($(du -h "$OUT" | cut -f1))"
unzip -l "$OUT" | grep -c "" | xargs echo "linhas na listagem:"
