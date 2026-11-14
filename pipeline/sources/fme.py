"""Questões de vestibular dos 8 volumes de Fundamentos de Matemática Elementar (recortes + gabarito)."""
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from books import crop_all, difficulty, exam_of, render_pages
from common import BOOKS, norm, topic_scores, write_out
from pdflines import page_count, page_lines

START = re.compile(r"^(\d{1,3})\.\s*\(([^)]{2,60})\)")
ANSWER = re.compile(r"^(\d{1,3})\.\s+([a-e])\s*\.?$")
OPTION = re.compile(r"(?:^|\s)([a-e])\)")

# tópico de cada volume quando o subtítulo da seção não decide
VOLUME_TOPIC = {
    1: "mat-conjuntos-funcoes", 2: "mat-log-exp", 3: "mat-trigonometria", 4: "mat-sequencias",
    5: "mat-combinatoria", 6: "mat-complexos-polinomios", 7: "mat-geometria-analitica", 8: "mat-limites-derivadas",
}
HEADING_TOPIC = [
    (r"conjunt|introducao as funcoes|funcao|funcoes|inequac|modul", "mat-conjuntos-funcoes"),
    (r"potencia|raiz|raizes|exponencial|logarit", "mat-log-exp"),
    (r"trigonom|seno|cosseno|arcos|triangulo|transformac|equacoes|inversas|ciclo", "mat-trigonometria"),
    (r"progress|sequenc", "mat-sequencias"),
    (r"matriz|determinant|sistema", "mat-matrizes-sistemas"),
    (r"binomio|combinat|arranjo|permut|contagem", "mat-combinatoria"),
    (r"probabil", "mat-probabilidade"),
    (r"complex|polinom|equacoes polinomiais|raizes multiplas", "mat-complexos-polinomios"),
    (r"reta|ponto|circunfer|conica|tangencia|distancia|lugares", "mat-geometria-analitica"),
    (r"limite|derivad|integral", "mat-limites-derivadas"),
]
# tópicos possíveis em cada volume: o subtítulo da seção escolhe entre eles, ou o texto decide
ALLOWED = {
    1: ["mat-conjuntos-funcoes", "mat-porcentagem", "mat-estatistica", "mat-aritmetica"],
    2: ["mat-log-exp"],
    3: ["mat-trigonometria"],
    4: ["mat-sequencias", "mat-matrizes-sistemas"],
    5: ["mat-combinatoria", "mat-probabilidade"],
    6: ["mat-complexos-polinomios"],
    7: ["mat-geometria-analitica"],
    8: ["mat-limites-derivadas"],
}


def topic_for(volume, heading, text):
    allowed = ALLOWED[volume]
    if len(allowed) == 1:
        return allowed[0]
    h = norm(heading)
    for pat, topic in HEADING_TOPIC:
        if h and re.search(pat, h) and topic in allowed:
            return topic
    scores = topic_scores(text, "mat")
    best = max(allowed, key=lambda t: scores[t])
    # nos volumes 1 e 5 o tópico principal vence empates e textos ambíguos
    return best if scores[best] >= 2 and scores[best] > scores[allowed[0]] else VOLUME_TOPIC[volume]


def is_heading(line, body_x, top, bottom):
    x0, y0, _, _, text = line
    return (x0 < body_x - 6 and top < y0 < bottom and len(text) < 70 and not re.match(r"^[\d(]", text)
            and not re.match(r"^[a-e]\)", text) and text[0].isupper() and not text.endswith((".", ":", ",")))


def body_indent(lines):
    """recuo mais comum do corpo do texto (os números das questões ficam à esquerda dele)"""
    xs = Counter(round(l[0]) for l in lines if not START.match(l[4]))
    return xs.most_common(1)[0][0] if xs else 60


def gap_above(lines, y):
    """corta no meio do espaço entre o conteúdo anterior e a linha em y"""
    above = [l[3] for l in lines if l[1] < y - 1 and l[3] <= y + 1]
    return (max(above) + y) / 2 if above else y - 3


def import_volume(volume):
    pdf = BOOKS / f"Fundamentos de matemática elementar - Vol. {volume:02d}.pdf"
    pages = page_lines(pdf, 1, page_count(pdf))
    header = lambda L, pat: any(re.search(pat, norm(l[4])) and l[1] < 75 for l in L)
    ans_pages = [p for p, (_, _, L) in pages.items() if header(L, r"respostas das questoes")]
    first_ans = ans_pages[0]
    q_pages = [p for p, (_, _, L) in pages.items() if p < first_ans and header(L, r"^questoes de vestibulares")]

    answers = {}
    for p in range(first_ans, min(first_ans + 25, max(pages) + 1)):
        for line in pages[p][2]:
            m = ANSWER.match(line[4])
            if m:
                answers.setdefault(int(m.group(1)), "abcde".index(m.group(2)))

    # 1) segmentos de cada questão, página a página
    questions, current, heading = [], None, ""
    for p in q_pages:
        w, h, L = pages[p]
        top = max((l[3] for l in L if l[1] < 75 and "QUEST" in l[4].upper()), default=60) + 4
        foot = min((l[1] for l in L if l[1] > h - 60), default=h - 40) - 14
        content = [l for l in L if top < l[1] < foot]
        bx = body_indent(content)
        starts = [l for l in content if START.match(l[4]) and l[0] < bx - 6]
        margin = min((l[0] for l in content if l[0] < bx - 6), default=bx - 20)
        right = min(w, max((l[2] for l in content), default=w - 40) + 6)
        cuts = sorted([(gap_above(L, l[1]), "q", l) for l in starts] +
                      [(gap_above(L, l[1]), "h", l) for l in content if is_heading(l, bx, top, foot) and not START.match(l[4])])
        y = top
        for cy, kind, line in cuts:
            if current is not None and cy - y > 8:
                current["segs"].append((p, margin - 6, y, right, cy))
            if kind == "h":
                heading, current = line[4], None
            else:
                m = START.match(line[4])
                current = {"num": int(m.group(1)), "inst": m.group(2), "heading": heading, "page": p, "segs": [], "text": []}
                questions.append(current)
            y = cy
        if current is not None and foot - y > 8:
            last = max((l[3] for l in content if l[1] >= y), default=y)
            current["segs"].append((p, margin - 6, y, right, min(foot, last + 40)))
        for line in L:  # texto bruto da questão, para contar alternativas e classificar
            owner = None
            for q in questions:
                for sp, _, sy0, _, sy1 in q["segs"]:
                    if sp == p and sy0 <= line[1] < sy1:
                        owner = q
            if owner:
                owner["text"].append(line[4])

    # continuação sem nenhuma linha de texto é só espaço em branco
    for q in questions:
        q["segs"] = [sg for k, sg in enumerate(q["segs"])
                     if k == 0 or any(sg[2] <= l[1] < sg[4] for l in pages[sg[0]][2])]

    # 2) só as de múltipla escolha com gabarito em letra
    by_heading = {}
    for q in questions:
        by_heading.setdefault(q["heading"], []).append(q)
    out, jobs = [], []
    for heading, group in by_heading.items():
        for pos, q in enumerate(group):
            ans = answers.get(q["num"])
            text = "\n".join(q["text"])
            letters = {c for c in OPTION.findall(text)}
            if ans is None or not q["segs"] or "a" not in letters and ans > 0:
                continue
            n = max(4, "abcde".index(max(letters)) + 1 if letters else 5, ans + 1)
            exam, year = exam_of(q["inst"])
            topic = topic_for(volume, heading, text)
            qid = f"fme{volume}-{q['num']}"
            names = [f"{qid}-{k}" for k in range(len(q["segs"]))]
            jobs += [(name, *seg) for name, seg in zip(names, q["segs"])]
            out.append({
                "id": qid, "s": "mat", "e": exam, "y": year, "t": topic, "d": difficulty(pos, len(group), exam),
                "k": "image", "opts": [], "n": n, "ans": ans, "imgs": [f"data/img/fme/{nm}.webp" for nm in names],
                "tags": [], "src": f"({q['inst']}) · Fundamentos de Matemática Elementar, vol. {volume}, questão {q['num']}, p. {q['page']}",
                "book": {"file": pdf.name, "page": q["page"]}, "heading": heading,
            })
    return out, jobs, pdf, {p for j in jobs for p in [j[1]]}


def main():
    all_q = []
    for volume in range(1, 9):
        qs, jobs, pdf, used = import_volume(volume)
        png = render_pages(pdf, sorted(used), f"fme{volume}")
        crop_all(jobs, png, "fme")
        print(f"vol. {volume}: {len(qs)} questões")
        all_q += qs
    write_out("fme", all_q)


if __name__ == "__main__":
    main()
