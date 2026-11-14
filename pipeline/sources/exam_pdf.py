"""Recorte genérico de provas em PDF com camada de texto: cada questão vai do seu rótulo até o próximo."""
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from books import crop_all, render_pages
from pdflines import page_count, page_lines

DIGITS = re.compile(r"\d+")


def margins(pages):
    """cabeçalho e rodapé: linhas que se repetem (ignorando números) no topo/pé de muitas páginas"""
    seen = Counter()
    for _, (w, h, L) in pages.items():
        # números soltos no topo costumam ser rótulos de questão, não cabeçalho
        keys = {DIGITS.sub("#", l[4]) for l in L if (l[1] < h * 0.09 and not l[4].strip().isdigit()) or l[3] > h * 0.91}
        seen.update(keys)
    repeated = {k for k, n in seen.items() if n >= max(2, len(pages) // 2)}
    out = {}
    for p, (w, h, L) in pages.items():
        heads = [l[3] for l in L if l[1] < h * 0.09 and not l[4].strip().isdigit() and DIGITS.sub("#", l[4]) in repeated]
        feet = [l[1] for l in L if l[3] > h * 0.91 and (DIGITS.sub("#", l[4]) in repeated or l[4].strip().isdigit())]
        out[p] = (max(heads, default=18) + 3, min(feet, default=h - 18) - 3)
    return out


def segment(pdf, start_re, stop_re=None):
    """{número: {"segs": [(pág, x0, y0, x1, y1)], "text": str, "page": int}}

    start_re casa o rótulo da questão (grupo 1 = número). stop_re marca linhas que encerram a questão
    anterior sem abrir outra (títulos de seção, instruções).
    """
    pages = page_lines(pdf, 1, page_count(pdf))
    bounds = margins(pages)
    questions, order, current = {}, [], None
    for p, (w, h, L) in pages.items():
        top, foot = bounds[p]
        content = [l for l in L if top <= l[1] and l[3] <= foot + 3]
        if not content:
            continue
        left = max(0, min(l[0] for l in content) - 8)
        right = max(min(w, max(l[2] for l in content) + 8), w - left)  # figuras passam do texto
        cuts = []
        for l in content:
            m = start_re.match(l[4])
            if m:
                cuts.append((l[1], int(m.group(1))))
            elif stop_re and stop_re.search(l[4]):
                cuts.append((l[1], None))
        cuts.sort()
        y = top
        for cy, num in cuts:
            above = [l[3] for l in content if l[1] < cy - 1 and l[3] <= cy + 1 and l[1] >= y]
            cut = (max(above) + cy) / 2 if above else cy - 3
            if current is not None and cut - y > 6:
                current["segs"].append((p, left, y, right, cut))
            if num is None or num in questions:  # número repetido = outra prova no mesmo PDF; ignora
                current = None
            else:
                current = questions[num] = {"segs": [], "text": [], "page": p}
                order.append(num)
            y = cut
        if current is not None:
            last = max((l[3] for l in content if l[1] >= y), default=y)
            if last - y > 6:
                current["segs"].append((p, left, y, right, min(foot, last + 30)))
        for l in content:
            for q in questions.values():
                if any(sp == p and sy0 <= l[1] < sy1 for sp, _, sy0, _, sy1 in q["segs"]):
                    q["text"].append(l[4])
                    break
    for q in questions.values():
        q["text"] = re.sub(r"(\w)-\n(\w)", r"\1\2", "\n".join(q["text"]))  # desfaz hifenização
        q["segs"] = [s for k, s in enumerate(q["segs"])
                     if k == 0 or any(s[2] <= l[1] < s[4] for l in pages[s[0]][2])]
    return questions


def crop_questions(pdf, questions, tag, folder):
    """recorta as questões escolhidas; devolve {número: [caminhos]}"""
    jobs, names = [], {}
    for num, q in questions.items():
        names[num] = [f"{tag}-{num}-{k}" for k in range(len(q["segs"]))]
        jobs += [(n, *s) for n, s in zip(names[num], q["segs"])]
    png = render_pages(pdf, sorted({j[1] for j in jobs}), tag)
    paths = iter(crop_all(jobs, png, folder))
    return {num: [next(paths) for _ in names[num]] for num in names}


def option_count(text):
    letters = set(re.findall(r"(?:^|\s)([A-E])\s?\(\s?\)", text)) or set(re.findall(r"(?:^|\s)\(?([A-E])\)", text))
    return max(4, "ABCDE".index(max(letters)) + 1) if letters else 5


def segment_columns(pdf, start_re, window=4):
    """como segment(), para provas em duas colunas com questões que às vezes ocupam a largura toda.

    Lê a página em faixas: colunas esquerda e direita até uma questão de largura total, a faixa dela,
    e de novo as colunas. Uma questão que chega ao pé da coluna continua no topo da seguinte.
    """
    pages = page_lines(pdf, 1, page_count(pdf))
    bounds = margins(pages)
    questions, current, last = {}, None, 0
    for p, (w, h, L) in pages.items():
        top, foot = bounds[p]
        content = [l for l in L if top <= l[1] and l[3] <= foot + 3]
        if not content:
            continue
        mid = w / 2
        lx = min(l[0] for l in content)
        rx = min((l[0] for l in content if l[0] > mid - 15), default=mid)
        starts = []
        for l in content:
            m = start_re.match(l[4])
            if m and (abs(l[0] - lx) < 12 or abs(l[0] - rx) < 12):
                starts.append((l[1], "L" if l[0] < mid - 15 else "R", int(m.group(1))))
        # número solto pode ser rótulo de eixo: só vale se seguir a numeração da prova
        kept = []
        for s in sorted(starts, key=lambda s: (s[1], s[0])):
            if s[2] not in questions and abs(s[2] - last) <= window and s[2] > 0:
                kept.append(s)
                last = max(last, s[2])
        starts = sorted(kept)

        def crosses(y0, y1):
            return any(l[0] < mid - 15 and l[2] > mid + 25 and y0 <= l[1] < y1 for l in content)

        # faixas de largura total: questão da coluna esquerda cujo texto atravessa o meio
        bands = []
        for k, (y, col, num) in enumerate(starts):
            if col != "L":
                continue
            nxt = min([s[0] for s in starts if s[0] > y + 1], default=foot)
            if crosses(y, nxt):
                bands.append((y, nxt, num))
        slots, y = [], top
        for by0, by1, num in bands:
            slots += [("L", y, by0), ("R", y, by0), ("F", by0, by1)]
            y = by1
        slots += [("L", y, foot), ("R", y, foot)]

        for col, y0, y1 in slots:
            if y1 - y0 < 6:
                continue
            x0, x1 = {"L": (lx - 6, mid - 2), "R": (rx - 6, w - lx + 6), "F": (lx - 6, w - lx + 6)}[col]
            inside = [l for l in content if y0 - 1 <= l[1] < y1 and (col == "F" or (l[0] < mid - 15) == (col == "L"))]
            cuts = sorted((s[0], s[2]) for s in starts if y0 - 1 <= s[0] < y1 and (col == "F" or s[1] == col))
            y = y0
            for cy, num in cuts:
                above = [l[3] for l in inside if y <= l[1] < cy - 1]
                cut = (max(above) + cy) / 2 if above else cy - 3
                if current is not None and cut - y > 6 and above:
                    current["segs"].append((p, x0, y, x1, cut))
                current = None if num in questions else questions.setdefault(num, {"segs": [], "text": [], "page": p})
                y = cut
            rest = [l for l in inside if l[1] >= y]
            if current is not None and rest:
                current["segs"].append((p, x0, y, x1, min(y1, max(l[3] for l in rest) + 30)))
            for l in inside:
                for q in questions.values():
                    if any(sp == p and sy0 <= l[1] < sy1 and sx0 <= l[0] < sx1 for sp, sx0, sy0, sx1, sy1 in q["segs"]):
                        q["text"].append(l[4])
                        break
    for q in questions.values():
        q["text"] = re.sub(r"(\w)-\n(\w)", r"\1\2", "\n".join(q["text"]))
    return questions
