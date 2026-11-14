"""Linhas de texto com coordenadas (pontos) via pdftotext -bbox-layout."""
import html
import re
import subprocess
import unicodedata

LINE = re.compile(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>', re.S)
WORD = re.compile(r">([^<]*)</word>")
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
PAGE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)


def page_lines(pdf, first, last):
    """{página: (largura, altura, [(x0, y0, x1, y1, texto), ...])} em ordem de leitura do PDF"""
    out = subprocess.run(["pdftotext", "-f", str(first), "-l", str(last), "-bbox-layout", str(pdf), "-"],
                         capture_output=True, text=True, check=True).stdout
    pages = {}
    for k, m in enumerate(PAGE.finditer(out)):
        lines = []
        for lm in LINE.finditer(m.group(3)):
            # NFC junta acentos decompostos ("a" + til) que alguns PDFs do LaTeX produzem
            text = unicodedata.normalize("NFC", html.unescape(" ".join(WORD.findall(lm.group(5))))).replace("ı́", "í")
            text = CONTROL.sub("", text).strip()
            if text:
                lines.append((float(lm.group(1)), float(lm.group(2)), float(lm.group(3)), float(lm.group(4)), text))
        pages[first + k] = (float(m.group(1)), float(m.group(2)), lines)
    return pages


def page_count(pdf):
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
    return int(re.search(r"Pages:\s+(\d+)", out).group(1))
