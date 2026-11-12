"""Gera relatorio/relatorio.pdf: Markdown -> (pandoc) HTML -> (Chrome headless) PDF.

    python relatorio/build.py --autores "Nome 1 e Nome 2"

Substitui {{RESULTADOS}} pelo conteúdo de relatorio/resultados.md e
{{CONCLUSAO}} pelo de relatorio/conclusao.md.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--autores", default="Nome 1 e Nome 2")
    args = ap.parse_args()
    md = (HERE / "relatorio.md").read_text(encoding="utf-8")
    for key, file in (("RESULTADOS", "resultados.md"), ("CONCLUSAO", "conclusao.md")):
        p = HERE / file
        md = md.replace("{{%s}}" % key, p.read_text(encoding="utf-8") if p.exists() else f"*({file} pendente)*")
    md = md.replace("{{AUTORES}}", args.autores)
    tmp_md = HERE / "_build.md"
    tmp_md.write_text(md, encoding="utf-8")
    html = HERE / "relatorio.html"
    subprocess.run(["pandoc", str(tmp_md), "-s", "--css", "style.css", "--embed-resources",
                    "--resource-path", str(HERE), "-f", "markdown+raw_html", "-o", str(html)],
                   check=True, cwd=HERE)
    tmp_md.unlink()
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    pdf = HERE / "relatorio.pdf"
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", html.as_uri()], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"OK: {pdf}")


if __name__ == "__main__":
    main()
