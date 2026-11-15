"""OCR (Tesseract, português) de PDFs escaneados, com linhas e coordenadas no mesmo formato de pdflines.

Uso: python3 ocr.py <pdf> <tag> [primeira] [última]   — preenche o cache em pipeline/raw/ocr/<tag>/
"""
import csv
import io
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PIPE, RAW
from pdflines import page_count

DPI = 300
PT = 72 / DPI
ENV = {**os.environ, "TESSDATA_PREFIX": str(PIPE / "tessdata"), "OMP_THREAD_LIMIT": "1"}


def _render(pdf, tag, first, last):
    """renderiza um lote de páginas num único processo (abrir o PDF escaneado é a parte cara)"""
    out = RAW / "ocr" / tag
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(["pdftoppm", "-f", str(first), "-l", str(last), "-r", str(DPI), "-gray", "-png", str(pdf), str(out / "p")], check=True)


def _tsv(tag, page, digits):
    out = RAW / "ocr" / tag / f"{page}.tsv"
    if not out.exists():
        png = RAW / "ocr" / tag / f"p-{page:0{digits}d}.png"
        tsv = subprocess.run(["tesseract", str(png), "-", "-l", "por", "--psm", "3", "tsv"],
                             capture_output=True, text=True, env=ENV, check=True).stdout
        out.write_text(tsv, encoding="utf-8")
        png.unlink()
    return out.read_text(encoding="utf-8")


def _mean_conf(tsv):
    confs = [float(r["conf"]) for r in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE)
             if r.get("level") == "5" and r["text"].strip() and float(r["conf"]) >= 0]
    return sum(confs) / len(confs) if confs else 0, len(confs)


def rotation(tag, page):
    f = RAW / "ocr" / tag / f"{page}.rot"
    return int(f.read_text()) if f.exists() else 0


def _fix_upside_down(pdf, tag, page):
    """página escaneada de cabeça para baixo: confiança baixa e o OSD do Tesseract manda girar 180°"""
    out = RAW / "ocr" / tag
    if (out / f"{page}.rot").exists():
        return
    tsv = (out / f"{page}.tsv").read_text(encoding="utf-8")
    conf, words = _mean_conf(tsv)
    if conf >= 60 or words < 15:
        (out / f"{page}.rot").write_text("0")
        return
    png = out / f"single-{page}"
    subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-r", str(DPI), "-gray", "-png", "-singlefile", str(pdf), str(png)], check=True)
    png = png.with_suffix(".png")
    osd = subprocess.run(["tesseract", str(png), "-", "--psm", "0"], capture_output=True, text=True, env=ENV).stdout
    rot = 180 if "Rotate: 180" in osd else 0
    if rot:
        subprocess.run(["magick", str(png), "-rotate", "180", str(png)], check=True)
        new = subprocess.run(["tesseract", str(png), "-", "-l", "por", "--psm", "3", "tsv"], capture_output=True, text=True, env=ENV, check=True).stdout
        if _mean_conf(new)[0] > conf:
            (out / f"{page}.tsv").write_text(new, encoding="utf-8")
        else:
            rot = 0
    (out / f"{page}.rot").write_text(str(rot))
    png.unlink()


def ocr_lines(pdf, tag, first, last, workers=14):
    """{página: (largura, altura, [(x0, y0, x1, y1, texto), ...])} em pontos, como pdflines.page_lines"""
    pages = list(range(first, last + 1))
    missing = [p for p in pages if not (RAW / "ocr" / tag / f"{p}.tsv").exists()]
    digits = len(str(page_count(pdf)))
    if missing:
        batches = [(missing[i], missing[min(i + 24, len(missing) - 1)]) for i in range(0, len(missing), 25)]
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(lambda b: _render(pdf, tag, *b), batches))
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(lambda p: _tsv(tag, p, digits), pages))
        list(ex.map(lambda p: _fix_upside_down(pdf, tag, p), pages))
    tsvs = {p: (RAW / "ocr" / tag / f"{p}.tsv").read_text(encoding="utf-8") for p in pages}
    result = {}
    for p, tsv in tsvs.items():
        rows = list(csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE))
        page = next((r for r in rows if r["level"] == "1"), None)
        w, h = (int(page["width"]) * PT, int(page["height"]) * PT) if page else (595, 842)
        lines = {}
        for r in rows:
            if r["level"] != "5" or not r["text"].strip() or float(r["conf"]) < 0:
                continue
            key = (r["block_num"], r["par_num"], r["line_num"])
            x0, y0 = int(r["left"]) * PT, int(r["top"]) * PT
            x1, y1 = x0 + int(r["width"]) * PT, y0 + int(r["height"]) * PT
            if key in lines:
                a = lines[key]
                lines[key] = (min(a[0], x0), min(a[1], y0), max(a[2], x1), max(a[3], y1), a[4] + " " + r["text"])
            else:
                lines[key] = (x0, y0, x1, y1, r["text"])
        result[p] = (w, h, sorted(lines.values(), key=lambda l: (l[1], l[0])))
    return result


if __name__ == "__main__":
    pdf, tag = Path(sys.argv[1]), sys.argv[2]
    first = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    last = int(sys.argv[4]) if len(sys.argv) > 4 else page_count(pdf)
    pages = ocr_lines(pdf, tag, first, last)
    print(f"{tag}: {len(pages)} páginas com OCR")
