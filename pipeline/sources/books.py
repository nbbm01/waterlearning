"""Partes comuns aos importadores de livros: banca, dificuldade, recorte de páginas."""
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import PUBLIC, RAW, norm

DPI = 144
SCALE = DPI / 72


def exam_of(inst):
    """(banca agrupada, ano) a partir do rótulo entre parênteses, ex.: 'Fuvest-SP 2010'"""
    year = re.search(r"\b(19[5-9]\d|20[0-3]\d)\b", inst)
    n = norm(inst)
    groups = [
        (r"^fuvest", "FUVEST"), (r"^unicamp", "UNICAMP"), (r"^(v?unesp)", "UNESP"), (r"^unifesp", "UNIFESP"),
        (r"^ita\b", "ITA"), (r"^ime\b", "IME"), (r"^afa\b", "AFA"), (r"^efomm", "EFOMM"), (r"^espcex|^esp\.?cex", "EsPCEx"),
        (r"^(en|escola naval)\b", "EN"), (r"^(cn|colegio naval)\b", "CN"), (r"^epcar", "EPCAr"), (r"^eear", "EEAR"),
        (r"^cmrj", "CMRJ"), (r"^enem", "ENEM"), (r"^(ue-rj|uerj)", "UERJ"), (r"^mackenzie", "Mackenzie"),
        (r"^puc", "PUC"), (r"^fgv", "FGV"), (r"^(uf|u\. ?f\.|ufrj|ufmg|ufpe|ufsc|ufrgs|ufpr|ufba|ufc|unb|utfpr|ufscar)", "Federais"),
    ]
    for pat, name in groups:
        if re.search(pat, n):
            return name, int(year.group(1)) if year else 0
    return "Outras", int(year.group(1)) if year else 0


TOUGH = {"ITA", "IME", "EN", "AFA", "EFOMM", "FUVEST", "UNICAMP"}


def difficulty(position, size, exam):
    """posição na seção (os livros vão do mais simples ao mais exigente) + peso da banca"""
    third = 1 + min(2, (3 * position) // max(size, 1))
    if exam in TOUGH:
        third += 1
    return max(1, min(3, third))


def render_pages(pdf, pages, tag):
    """renderiza cada página uma vez (cache em pipeline/raw/pages/<tag>)"""
    out = RAW / "pages" / tag
    out.mkdir(parents=True, exist_ok=True)

    def one(p):
        target = out / f"{p}.png"
        if not target.exists():
            subprocess.run(["pdftoppm", "-f", str(p), "-l", str(p), "-r", str(DPI), "-gray", "-png", "-singlefile",
                            str(pdf), str(out / str(p))], check=True)
        return p, target

    with ThreadPoolExecutor(8) as ex:
        return dict(ex.map(one, pages))


def crop_all(jobs, page_png, folder):
    """jobs: [(nome, página, x0, y0, x1, y1) em pontos] → webp em public/data/img/<folder>"""
    dest = PUBLIC / "img" / folder
    dest.mkdir(parents=True, exist_ok=True)

    def one(job):
        name, page, x0, y0, x1, y1 = job
        target = dest / f"{name}.webp"
        if not target.exists():
            geo = f"{round((x1 - x0) * SCALE)}x{round((y1 - y0) * SCALE)}+{round(x0 * SCALE)}+{round(y0 * SCALE)}"
            subprocess.run(["magick", str(page_png[page]), "-crop", geo, "+repage", "-trim", "-bordercolor", "white",
                            "-border", "12", "-quality", "80", "-define", "webp:lossless=false", str(target)], check=True)
        return f"data/img/{folder}/{name}.webp"

    with ThreadPoolExecutor(8) as ex:
        return list(ex.map(one, jobs))
