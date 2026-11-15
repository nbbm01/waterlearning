"""TQM (Roberto Ávila), livros escaneados: questões de vestibular por capítulo, em ordem crescente de dificuldade.

O texto vem do OCR (pipeline/ocr.py) só para achar números, gabarito e capítulos; a questão em si
entra como recorte fiel da página.
Uso: python3 tqm.py fundamental|medio
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from books import exam_of
from common import BOOKS, TAXONOMY, best_topic, norm, write_out
from exam_pdf import crop_questions, option_count, segment_columns
from ocr import ocr_lines, rotation
from pdflines import page_count

BOOKS_CFG = {
    "fundamental": ("tqm.pdf", "tqmf", "TQM Ensino Fundamental"),
    "medio": ("TQM Ensino Médio (Roberto Ávila) (z-library.sk, 1lib.sk, z-lib.sk).pdf", "tqmm", "TQM Ensino Médio"),
}
# rótulo da questão: "58)" (o OCR às vezes lê o parêntese como } ou ])
START = re.compile(r"^(\d{1,3})\s*[)}\]](?!\s*[A-E€]\s*$)(?!\s*[a-e]\)\s)")
# linha de gabarito: "49) B", "61)D", "69) €"
ANSWER = re.compile(r"^(\d{1,3})\s*[)}\]]\s*€?([A-E€])\s*$")
ANY_ANSWER = re.compile(r"^(\d{1,3})\s*[)}\]]\s*\S")
HEADER = re.compile(r"Cap[íi1l][tf]u[lt1]o\s*(\d{1,2})", re.I)

# capítulo (pelo título) → (tópico, subtópico); a primeira regra que casar vale
TITLE_MAP = [
    (r"numera", "mat-aritmetica", "mat-potencias-notacao"),
    (r"numeros (inteiros|proporcionais|naturais|racionais)", "mat-aritmetica", None),
    (r"expressoes algebricas|algebra", "mat-conjuntos-funcoes", "mat-algebra-basica"),
    (r"operac", "mat-aritmetica", "mat-fracoes-decimais"),
    (r"primos|divisibilidade|divisor|multiplo", "mat-aritmetica", "mat-divisibilidade"),
    (r"frac|decima|dizima", "mat-aritmetica", "mat-fracoes-decimais"),
    (r"razao|proporc|regra de tres|grandezas", "mat-aritmetica", "mat-razao-proporcao"),
    (r"porcent|juros", "mat-porcentagem", "mat-porcentagem-basica"),
    (r"media", "mat-estatistica", "mat-medias"),
    (r"medidas|unidades", "mat-grandezas-medidas", "mat-conversao"),
    (r"conjunto", "mat-conjuntos-funcoes", "mat-conjuntos"),
    (r"produtos notaveis|fatora|fracoes algebricas|expressoes algebricas|polinomio|monomio|calculo algebrico", "mat-conjuntos-funcoes", "mat-algebra-basica"),
    (r"inequac", "mat-conjuntos-funcoes", "mat-inequacoes"),
    (r"(problemas|sistemas?)( de equacoes)? do:? 1|equac\w* do:? 1", "mat-conjuntos-funcoes", "mat-equacao-1grau"),
    (r"(problemas|equac\w*) do 2|biquadrad|irraciona", "mat-conjuntos-funcoes", "mat-equacao-2grau"),
    (r"funcao do 2|funcao quadratica", "mat-conjuntos-funcoes", "mat-funcao-quadratica"),
    (r"funcao do 1|funcao afim", "mat-conjuntos-funcoes", "mat-funcao-afim"),
    (r"funco", "mat-conjuntos-funcoes", "mat-funcoes-intro"),
    (r"potenc|radica|raiz", "mat-log-exp", "mat-potencias-raizes"),
    (r"exponencia", "mat-log-exp", "mat-exponencial"),
    (r"logarit", "mat-log-exp", "mat-logaritmos"),
    (r"angulo|poligono|quadrilatero", "mat-geometria-plana", "mat-poligonos-angulos"),
    (r"triangulo|linhas proporcionais|relacoes metricas|semelhan", "mat-geometria-plana", "mat-triangulos"),
    (r"razoes trigonometricas|trigonometri", "mat-trigonometria", None),
    (r"circulo|circunferencia", "mat-geometria-plana", "mat-circunferencia-plana"),
    (r"area", "mat-geometria-plana", "mat-areas"),
    (r"progress", "mat-sequencias", None),
    (r"matriz|determinant|sistemas lineares", "mat-matrizes-sistemas", None),
    (r"combinat|binomio", "mat-combinatoria", None),
    (r"probabil", "mat-probabilidade", None),
    (r"estatistic|grafico", "mat-estatistica", None),
    (r"complex", "mat-complexos-polinomios", "mat-complexos"),
    (r"prisma|piramide|cilindro|cone|esfera|poliedro|solido|espacial|volume", "mat-geometria-espacial", None),
    (r"reta|ponto|plano cartesiano|analitica|conica|elipse|hiperbole|vetor", "mat-geometria-analitica", None),
]
TOUGH_SCHOOLS = {"CN", "EPCAr", "CMRJ", "ITA", "IME", "EN", "AFA", "EFOMM", "EsPCEx"}


def garbage(token):
    """as linhas pontilhadas do sumário viram "eee rreerenraorere..." no OCR"""
    t = norm(token)
    letters = [c for c in t if c.isalpha()]
    if not letters:
        return True
    rea = sum(c in "rea" for c in letters) / len(letters)
    return (len(letters) >= 3 and rea >= 0.8) or len(re.findall(r"(ee|rr|aa)", t)) >= 2


def clean_toc(text):
    words = []
    for token in text.replace("|", " ").split():
        if garbage(token) and words:
            break
        if not garbage(token):
            words.append(token)
    return " ".join(words).strip(" .,-")


def toc_titles(pages, last_toc_page):
    """{capítulo: título} a partir das linhas "Capítulo N" + título no sumário"""
    titles = {}
    for p in range(1, last_toc_page + 1):
        lines = [l[4] for l in pages[p][2]]
        for i, text in enumerate(lines):
            m = HEADER.search(text)
            if not m:
                continue
            rest = text[m.end():].strip(" |-")
            cand = rest if len(rest) > 3 else (lines[i + 1] if i + 1 < len(lines) else "")
            title = clean_toc(re.split(r"\s*\.{2,}|\s{2,}|…", cand)[0])
            if title and int(m.group(1)) not in titles and not HEADER.search(title):
                titles[int(m.group(1))] = title
    return titles


def chapter_of_pages(pages):
    """capítulo de cada página pelo cabeçalho; onde o OCR falha, herda o da página anterior.
    O sumário também diz "Capítulo N", então a contagem só começa no capítulo 1 e anda para a frente."""
    out, current = {}, None
    for p in sorted(pages):
        w, h, L = pages[p]
        head = " ".join(l[4] for l in L if l[1] < h * 0.07)
        m = HEADER.search(head)
        if m:
            n = int(m.group(1))
            if (current is None and n == 1) or (current is not None and 0 <= n - current <= 6):
                current = n
        out[p] = current
    return out


def first_page_titles(pages, chapters):
    """título na abertura do capítulo: a linha logo abaixo de "Capítulo N", em letra grande"""
    titles = {}
    for p in sorted(pages):
        c = chapters.get(p)
        if c is None or c in titles:
            continue
        w, h, L = pages[p]
        top = sorted((l for l in L if l[1] < h * 0.2), key=lambda l: l[1])
        for i, l in enumerate(top):
            m = HEADER.search(l[4])
            if m and int(m.group(1)) == c:
                rest = l[4][m.end():].strip(" |-:")
                below = [x for x in top[i + 1:] if 0 < x[1] - l[1] < 45 and len(x[4]) > 3]
                title = rest if len(rest) > 3 else (below[0][4] if below else "")
                if title:
                    titles[c] = title.strip(" |-.")
                break
    return titles


ANSWER_LINE = re.compile(r"^(\d{1,3})\s*[)}\]]\s*(\S.{0,24})$")


def answers_in(pages, chapter_pages):
    """gabarito do capítulo, a partir das páginas de respostas (muitas linhas curtas "N) resposta").

    O quadro tem várias colunas lado a lado, então não dá para confiar na ordem de leitura do OCR.
    Um número que aparece duas vezes indica leitura errada ("110" lido como "10"): os dois são
    descartados, porque é melhor perder uma questão do que mostrar gabarito errado."""
    seen, letters = {}, {}
    for p in chapter_pages:
        lines = [l[4].strip() for l in pages[p][2]]
        answers = [m for m in (ANSWER_LINE.match(t) for t in lines) if m and not m.group(2).startswith("(")]
        if len(answers) < 8:
            continue
        for m in answers:
            n = int(m.group(1))
            seen[n] = seen.get(n, 0) + 1
            a = ANSWER.match(m.group(0))
            if a:
                letters[n] = "ABCDE".index(a.group(2).replace("€", "E"))
    return {n: v for n, v in letters.items() if seen[n] == 1}


def clean_single(n, text):
    """recorte confiável: começa pelo próprio número, tem cada alternativa uma vez e nenhum outro rótulo.
    Quando o OCR perde um número, duas questões grudam no mesmo recorte; essas ficam de fora."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines or not re.match(rf"^{n}\s*[)}}\]]", lines[0]):
        return False
    if any(re.match(r"^\d{1,3}\s*[)}\]]", l) for l in lines[1:]):
        return False
    # rótulo que o OCR leu sem parêntese ("30" sozinho) ou banca abrindo outra questão ("(CN) Na figura...")
    if any(re.fullmatch(rf"{k}\W?", l) for l in lines[1:] for k in range(n + 1, n + 4)):
        return False
    if any(re.match(r"^\(?[A-ZÉ][A-Za-zÉ. ]{1,14}\)\s+[A-ZÉ]", l) for l in lines[1:]):
        return False
    opts = [m.lower() for l in lines for m in re.findall(r"^([a-eA-E])\s?\)", l)]
    if len(opts) != len(set(opts)):
        return False
    return multiple_choice(text) and len(text) < 1800


def multiple_choice(text):
    letters = set(re.findall(r"(?:^|\s)([a-eA-E])\s?\)", text))
    return len(letters & set("abcd")) >= 3 or len(letters & set("ABCD")) >= 3


def map_title(title):
    t = norm(title)
    for pat, topic, sub in TITLE_MAP:
        if re.search(pat, t):
            return topic, sub
    return None, None


def answer_page(page):
    lines = [l[4].strip() for l in page[2]]
    return sum(1 for t in lines if (m := ANSWER_LINE.match(t)) and not m.group(2).startswith("(")) >= 8


def chapters_by_answer_blocks(pages):
    """sem cabeçalho de capítulo: cada capítulo termina no seu bloco de páginas de gabarito"""
    out, chapter, prev_answer = {}, 1, False
    for p in sorted(pages):
        is_answer = answer_page(pages[p])
        if prev_answer and not is_answer:
            chapter += 1
        out[p] = chapter
        prev_answer = is_answer
    return out


def topic_name(topic_id):
    return next(t["name"] for s in TAXONOMY["subjects"] for t in s["topics"] if t["id"] == topic_id)


def main(which):
    file, tag, label = BOOKS_CFG[which]
    pdf = BOOKS / file
    pages = ocr_lines(pdf, tag, 1, page_count(pdf))
    chapters = chapter_of_pages(pages)
    if not any(chapters.values()):
        chapters = chapters_by_answer_blocks(pages)
    first_content = min(p for p, c in chapters.items() if c is not None)
    toc = toc_titles(pages, first_content - 1)
    opening = first_page_titles(pages, chapters)
    by_chapter = {}
    for p, c in chapters.items():
        if c is not None:
            by_chapter.setdefault(c, []).append(p)
    out = []
    for c, cpages in sorted(by_chapter.items()):
        # o sumário e a página de abertura têm erros de OCR diferentes: vale o primeiro que casar com um assunto
        title, topic, sub = f"Capítulo {c}", None, None
        for cand in (toc.get(c), opening.get(c)):
            if cand and not topic:
                topic, sub = map_title(cand)
                if topic:
                    title = cand
        if not topic and not toc and not opening:
            # assunto do capítulo pela soma do texto de todas as páginas: bem mais estável que questão a questão
            text = "\n".join(l[4] for p in cpages for l in pages[p][2])
            topic, score = best_topic(text, "mat")
            if score < 25:
                topic = None
            title = topic_name(topic) if topic else title
        if not topic:
            print(f"  cap. {c} ({title}): fora de Matemática básica mapeada, ignorado")
            continue
        key = answers_in(pages, cpages)
        if not key:
            continue
        subset = {p: pages[p] for p in cpages}
        # OCR perde números aqui e ali: a janela de sequência é mais larga que nas provas digitais
        qs = segment_columns(pdf, START, window=15, pages=subset, stop_re=ANSWER, tight=True)
        # só múltipla escolha de verdade: o texto precisa ter as alternativas (evita listas da teoria)
        chosen = {n: q for n, q in qs.items() if n in key and len(q["segs"]) == 1 and clean_single(n, q["text"])}
        if not chosen:
            continue
        rot = {p: rotation(tag, p) for p in cpages}
        imgs = crop_questions(pdf, chosen, f"{tag}c{c}", tag, rot)
        nums = sorted(chosen)
        for pos, n in enumerate(nums):
            q = chosen[n]
            tagm = re.search(r"\(([A-Za-zÀ-ú.\- ]{2,30})\)", q["text"][:60])
            exam, year = exam_of(tagm.group(1)) if tagm else ("Livros", 0)
            if exam in ("Outras", "Federais") and not tagm:
                exam = "Livros"
            third = 1 + min(2, (3 * pos) // max(len(nums), 1))
            d = min(3, third + (1 if exam in TOUGH_SCHOOLS else 0))
            out.append({
                "id": f"{tag}-{c}-{n}", "s": "mat", "e": exam, "y": year, "t": topic, "d": d, "keep_d": True,
                "k": "image", "opts": [], "n": max(option_count(q["text"].replace("\n", " ")), key[n] + 1), "ans": key[n],
                "imgs": imgs[n], "tags": [], "raw": q["text"], "hint": title, **({"u": sub} if sub else {}),
                "src": f"{'(' + tagm.group(1) + ') · ' if tagm else ''}{label}, cap. {c} ({title}), questão {n}",
                "book": {"file": file, "page": q["page"]},
            })
        print(f"  cap. {c} {title}: {len(chosen)} questões (gabarito com {len(key)})")
    write_out(tag, out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "fundamental")
