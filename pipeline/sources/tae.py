"""Exercícios de múltipla escolha do livro Tópicos de Álgebra Elementar (Pedra, Monteiro, Ávila), por capítulo."""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from books import difficulty, exam_of
from common import BOOKS, write_out
from exam_pdf import crop_questions, option_count, segment
from pdflines import page_count, page_lines

PDF = BOOKS / "Tópicos de Álgebra Elementar (Bruno Pedra, Ivan Monteiro, Alex Ricardo) (z-library.sk, 1lib.sk, z-lib.sk).pdf"
START = re.compile(r"^(\d{1,3})\s*\)\s*\S")
TAG = re.compile(r"^\d{1,3}\s*\)\s*\(([^)]{2,40})\)")
# (página inicial, capítulo, tópico, subtópico) — na edição, página impressa = página do PDF
CHAPTERS = [
    (11, "Fundamentos da teoria dos conjuntos", "mat-conjuntos-funcoes", "mat-conjuntos"),
    (37, "Módulo de um número real", "mat-conjuntos-funcoes", "mat-funcao-modular"),
    (48, "Polinômios", "mat-complexos-polinomios", "mat-polinomios"),
    (73, "Produtos notáveis", "mat-conjuntos-funcoes", "mat-algebra-basica"),
    (89, "Fatoração", "mat-conjuntos-funcoes", "mat-algebra-basica"),
    (106, "Frações algébricas", "mat-conjuntos-funcoes", "mat-algebra-basica"),
    (126, "Equação do primeiro grau", "mat-conjuntos-funcoes", "mat-equacao-1grau"),
    (142, "Função do 1º grau", "mat-conjuntos-funcoes", "mat-funcao-afim"),
    (164, "Equações diofantinas lineares", "mat-aritmetica", "mat-divisibilidade"),
    (176, "Sistemas de equações do primeiro grau", "mat-conjuntos-funcoes", "mat-equacao-1grau"),
    (197, "Desigualdades elementares", "mat-conjuntos-funcoes", "mat-inequacoes"),
    (216, "Inequações do primeiro grau", "mat-conjuntos-funcoes", "mat-inequacoes"),
    (231, "Equação do segundo grau", "mat-conjuntos-funcoes", "mat-equacao-2grau"),
    (253, "Trinômio do segundo grau", "mat-conjuntos-funcoes", "mat-funcao-quadratica"),
    (272, "Função do 2º grau", "mat-conjuntos-funcoes", "mat-funcao-quadratica"),
    (309, "Tópicos de álgebra elementar", "mat-conjuntos-funcoes", None),
    (320, "Equação irracional", "mat-log-exp", "mat-potencias-raizes"),
    (336, "Inequação irracional", "mat-conjuntos-funcoes", "mat-inequacoes"),
    (348, "Transformação de expressões", "mat-log-exp", "mat-potencias-raizes"),
    (360, "Miscelânea de questões", "mat-conjuntos-funcoes", None),
    (399, None, None, None),
]


PAIR = re.compile(r"(?<!\d)(\d{1,3})\s*\)\s*\(?([a-e])\)?(?=\s|$)")


def answers_in(first, last):
    """gabarito do capítulo: a primeira página com várias linhas que são só "N) letra" """
    pages = page_lines(PDF, first, last)
    pure = {p: [l for l in L if re.fullmatch(r"(?:\d{1,3}\s*\)\s*\(?[a-e]\)?\s*)+", l[4])] for p, (_, _, L) in pages.items()}
    start = next((p for p in sorted(pure) if len(pure[p]) >= 3), None)
    key = {}
    if start is not None:
        for p in range(start, last + 1):
            for line in pure.get(p, []):
                for n, a in PAIR.findall(line[4]):
                    key.setdefault(int(n), "abcde".index(a))
    if start is None or start <= first:
        # sem linhas "N) letra" soltas: procura o título "RESPOSTAS DOS EXERCÍCIOS"
        start = next((p for p, (_, _, L) in pages.items() if p > first and any("RESPOSTAS DOS EXERC" in l[4].upper() for l in L)), None)
        if start is None:
            return None, {}
        text = subprocess.run(["pdftotext", "-f", str(start), "-l", str(last), "-layout", str(PDF), "-"],
                              capture_output=True, text=True, check=True).stdout
        key = {int(n): "abcde".index(a.lower()) for n, a in re.findall(r"(?<!\d)(\d{1,3})\s*[).]\s*\(?([a-eA-E])\)?(?=\s|$)", text)}
    return start, key


def main():
    out = []
    total = page_count(PDF)
    for (first, name, topic, sub), (nxt, *_) in zip(CHAPTERS, CHAPTERS[1:]):
        last = min(nxt - 1, total)
        ans_page, key = answers_in(first, last)
        if not ans_page or not key or ans_page <= first:
            print(f"{name}: sem gabarito em letras")
            continue
        # recorta só as páginas de exercícios, antes das respostas
        tmp = segment(PDF, START, first=first, last=ans_page - 1)
        chosen = {n: q for n, q in tmp.items() if n in key and q["segs"]}
        imgs = crop_questions(PDF, chosen, f"tae{first}", "tae")
        nums = sorted(chosen)
        for pos, n in enumerate(nums):
            q = chosen[n]
            tag = TAG.match(q["text"])
            exam, year = exam_of(tag.group(1)) if tag else ("Livros", 0)
            out.append({
                "id": f"tae-{first}-{n}", "s": "mat", "e": exam, "y": year, "t": topic, "d": difficulty(pos, len(nums), exam),
                "k": "image", "opts": [], "n": max(option_count(q["text"].replace("\n", " ")), key[n] + 1), "ans": key[n],
                "imgs": imgs[n], "tags": [], "raw": q["text"], "hint": "" if sub is None else name,
                "src": f"{'(' + tag.group(1) + ') · ' if tag else ''}Tópicos de Álgebra Elementar, {name}, exercício {n}, p. {q['page']}",
                "book": {"file": PDF.name, "page": q["page"]},
            })
        print(f"{name}: {len(chosen)} questões de múltipla escolha")
    write_out("tae", out)


if __name__ == "__main__":
    main()
