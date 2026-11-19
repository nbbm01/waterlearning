"""Converte o cache baixado por qdq_fetch.py (EsPCEx via API das Questões) para o formato do banco."""
import hashlib
import html
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import DEFAULT_TOPIC, PUBLIC, RAW, best_topic, classify_topic, norm, write_out

SRC = RAW / "qdq" / "questions"
IMG = PUBLIC / "img" / "qdq"
DIFF = {"FACIL": 1, "MEDIO": 2, "DIFICIL": 3}
DEFAULT = {"mat": "mat-conjuntos-funcoes", "fis": "fis-dinamica", "his": "his-brasil-contemporaneo"}
IMG_TAG = re.compile(r'<img[^>]+src="([^"]+)"[^>]*>', re.I)


def local_name(url):
    ext = Path(url.split("?")[0]).suffix.lower() or ".png"
    return hashlib.sha1(url.encode()).hexdigest()[:16] + ext


# tópico da API (sem acento, minúsculo) → (nosso tópico, subtópico); a primeira regra que casar vale
API_MAP = [
    (r"inequacoes de primeiro grau", "mat-conjuntos-funcoes", "mat-inequacoes"),
    (r"(?<!in)equacoes? de primeiro grau", "mat-conjuntos-funcoes", "mat-equacao-1grau"),
    (r"funcao de primeiro grau", "mat-conjuntos-funcoes", "mat-funcao-afim"),
    (r"inequacoes de primeiro grau", "mat-conjuntos-funcoes", "mat-inequacoes"),
    (r"(?<!in)equacoes de segundo grau|biquadrad", "mat-conjuntos-funcoes", "mat-equacao-2grau"),
    (r"funcao de segundo grau", "mat-conjuntos-funcoes", "mat-funcao-quadratica"),
    (r"inequacoes de segundo grau|outras inequacoes", "mat-conjuntos-funcoes", "mat-inequacoes"),
    (r"modular", "mat-conjuntos-funcoes", "mat-funcao-modular"),
    (r"funcao composta|funcao inversa", "mat-conjuntos-funcoes", "mat-funcao-composta-inversa"),
    (r"outras questoes sobre funcoes|definicao, interpretacao grafica|injetora", "mat-conjuntos-funcoes", "mat-funcoes-intro"),
    (r"^conjuntos|subconjuntos|numero de elementos da uniao", "mat-conjuntos-funcoes", "mat-conjuntos"),
    (r"numeros (naturais|inteiros|racionais|irracionais|reais)", "mat-conjuntos-funcoes", "mat-conjuntos-numericos"),
    (r"produtos notaveis|expressoes algebricas", "mat-conjuntos-funcoes", "mat-algebra-basica"),
    (r"outras equacoes", "mat-conjuntos-funcoes", None),
    (r"equacoes exponenciais|funcao exponencial", "mat-log-exp", "mat-exponencial"),
    (r"equacoes logaritmicas|funcao logaritmica", "mat-log-exp", "mat-funcao-logaritmica"),
    (r"^logaritmo", "mat-log-exp", "mat-logaritmos"),
    (r"radiciacao|potenciacao", "mat-log-exp", "mat-potencias-raizes"),
    (r"progressao aritmetica", "mat-sequencias", "mat-pa"),
    (r"progressao geometrica", "mat-sequencias", "mat-pg"),
    (r"^matrizes", "mat-matrizes-sistemas", "mat-matrizes"),
    (r"determinantes", "mat-matrizes-sistemas", "mat-determinantes"),
    (r"sistemas lineares", "mat-matrizes-sistemas", "mat-sistemas-lineares"),
    (r"analise combinatoria", "mat-combinatoria", None),
    (r"binomio|triangulo de pascal", "mat-complexos-polinomios", "mat-polinomios"),
    (r"probabilidade", "mat-probabilidade", None),
    (r"estatistica|media|mediana|moda", "mat-estatistica", None),
    (r"graficos e tabelas", "mat-estatistica", "mat-graficos-tabelas"),
    (r"numeros complexos", "mat-complexos-polinomios", "mat-complexos"),
    (r"polinomios", "mat-complexos-polinomios", None),
    (r"lei dos senos", "mat-trigonometria", "mat-trig-leis"),
    (r"seno e cosseno no triangulo retangulo", "mat-trigonometria", "mat-trig-triangulo"),
    (r"trigonometric|ciclo trigonometrico", "mat-trigonometria", None),
    (r"geometria analitica|retas|circunferencia.*analitic|conicas", "mat-geometria-analitica", None),
    (r"prismas|cubo|paralelepipedo", "mat-geometria-espacial", "mat-prismas"),
    (r"cilindro", "mat-geometria-espacial", "mat-cilindros"),
    (r"cone|piramide", "mat-geometria-espacial", "mat-cones-piramides"),
    (r"esfera", "mat-geometria-espacial", "mat-esferas"),
    (r"poliedros|euler", "mat-geometria-espacial", "mat-poliedros"),
    (r"geometria espacial|solidos", "mat-geometria-espacial", None),
    (r"triangul|tales|pitagoras|bissetriz|pontos notaveis", "mat-geometria-plana", "mat-triangulos"),
    (r"circunferencia|circulo", "mat-geometria-plana", "mat-circunferencia-plana"),
    (r"quadrilateros|poligonos|angulos", "mat-geometria-plana", "mat-poligonos-angulos"),
    (r"area|perimetro|geometria plana", "mat-geometria-plana", "mat-areas"),
    (r"regra de tres|proporc|razao", "mat-aritmetica", "mat-razao-proporcao"),
    (r"porcentagem", "mat-porcentagem", "mat-porcentagem-basica"),
    (r"juros simples", "mat-porcentagem", "mat-juros-simples"),
    (r"juros compostos|matematica financeira", "mat-porcentagem", "mat-juros-compostos"),
    (r"divisibilidade|mmc|mdc|primos", "mat-aritmetica", "mat-divisibilidade"),
    (r"fracoes|decimais|dizimas", "mat-aritmetica", "mat-fracoes-decimais"),
    (r"unidades de medida", "mat-grandezas-medidas", "mat-conversao"),
    (r"cinematica escalar", "fis-cinematica", None),
    (r"cinematica vetorial|lancamento", "fis-cinematica", "fis-queda-lancamentos"),
    (r"cinematica angular", "fis-cinematica", "fis-movimento-circular"),
    (r"leis de newton|conceitos iniciais de dinamica|polias|tracao", "fis-dinamica", "fis-leis-newton"),
    (r"plano inclinado|atrito", "fis-dinamica", "fis-atrito-plano"),
    (r"equilibrio|torque|estatica", "fis-dinamica", "fis-estatica"),
    (r"dinamica.*circular|centripeta", "fis-dinamica", "fis-centripeta"),
    (r"elastic|hooke", "fis-dinamica", "fis-molas"),
    (r"quantidade de movimento|impulso|colis", "fis-energia", "fis-impulso-colisoes"),
    (r"energia|trabalho e potencia", "fis-energia", "fis-trabalho-energia"),
    (r"gravitacao", "fis-gravitacao", "fis-kepler-newton"),
    (r"fluidostatica|hidrostatica|empuxo|pressao", "fis-hidrostatica", None),
    (r"dilatacao|temperatura|calor|calorimetria", "fis-termologia", None),
    (r"gases|entropia|segunda lei|maquinas termicas|termodinamica", "fis-termologia", "fis-gases-termodinamica"),
    (r"espelho|reflexao", "fis-optica", "fis-reflexao-espelhos"),
    (r"refracao", "fis-optica", "fis-refracao"),
    (r"lentes|instrumentos opticos|olho", "fis-optica", "fis-lentes-visao"),
    (r"optica|luz", "fis-optica", None),
    (r"oscilac|harmonico", "fis-ondulatoria", "fis-mhs"),
    (r"acustica|som", "fis-ondulatoria", "fis-acustica"),
    (r"ondas", "fis-ondulatoria", "fis-ondas"),
    (r"eletrizacao|campo eletrico|potencial eletrico|forca eletrica", "fis-eletricidade", "fis-eletrostatica"),
    (r"capacitor|gerador|receptor", "fis-eletricidade", "fis-capacitores-geradores"),
    (r"circuito|resistor|kirchhoff|wheatstone|corrente eletrica", "fis-eletricidade", "fis-circuitos"),
    (r"potencia eletrica|energia eletrica", "fis-eletricidade", "fis-potencia-consumo"),
    (r"inducao|faraday|lenz|transformador", "fis-eletromagnetismo", "fis-inducao"),
    (r"ima|campo magnetico|forca magnetica|magnetismo", "fis-eletromagnetismo", "fis-campo-forca-magnetica"),
    (r"relatividade|nuclear|radioativ", "fis-moderna", "fis-relatividade-nuclear"),
    (r"fotoeletric|quantica|modelos atomicos", "fis-moderna", "fis-quantica"),
]


def map_api_topic(name, subject):
    n = norm(name)
    for pat, topic, sub in API_MAP:
        if topic.startswith(subject) and re.search(pat, n):
            return topic, sub
    return None, None


def to_markdown(fragment, images):
    def img(m):
        images.add(m.group(1))
        return f"\n\n![](data/img/qdq/{local_name(m.group(1))})\n\n"
    text = IMG_TAG.sub(img, fragment or "")
    text = re.sub(r"</?(strong|b)>", "**", text, flags=re.I)
    text = re.sub(r"</?(em|i)>", "*", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>\s*", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"\*\*\s*\*\*", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text_out_of_math(wrap_math(re.sub(r"\n{3,}", "\n\n", text).strip()))


DELIMITED = re.compile(r"(\\\(.*?\\\)|\\\[.*?\\\]|\$\$.*?\$\$|!\[\]\([^)]*\))", re.S)
MATHY = re.compile(r"^[\w().,;:=+\-*/<>|\[\]^_{}\\'!°∈∉⊂⊃⊆⊇∪∩≤≥⩾⩽≠±×÷·→∞]+$")
WORDS = {"e", "a", "o", "de", "da", "do", "em", "ou", "que", "os", "as", "se", "um", "uma", "é", "no", "na"}


# palavras do enunciado que a API deixa dentro da fórmula ("com x > 0", "a inequaçãox^2 tem como")
PT = re.compile(r"(?<![\\a-zA-Z{])(com|tem|como|para|sendo|onde|que|qual|todo|toda|entre|seja|tal|rad|real|reais|"
                r"[a-záéíóúâêôãõç]*[áéíóúâêôãõç][a-záéíóúâêôãõç]*)(?![a-zA-Z}])")


def text_out_of_math(text):
    """dentro de \\( \\), palavra em português vira \\text{...}: senão sai em itálico e sem espaços"""
    def fix(m):
        body = re.sub(r"(ção|ções)(?=[a-z])", r"\1 ", m.group(1))  # "inequaçãox" → "inequação x"
        body = PT.sub(lambda w: f"\\text{{ {w.group(0)} }}", body)
        body = re.sub(r"(?<= )(e|ou)(?= )", r"\\text{\1}", body)  # conectivo solto; e^x fica
        return f"\\({body}\\)"
    return re.sub(r"\\\((.+?)\\\)", fix, text, flags=re.S)


def wrap_math(text):
    """envolve LaTeX solto em \\( \\): agrupa palavras vizinhas com cara de fórmula"""
    text = re.sub(r"(?<!\$)\$([^$\n]+?)\$(?!\$)", lambda m: f"\\({m.group(1)}\\)" if re.search(r"[\\^_{]", m.group(1)) else m.group(0), text)
    # ambientes (matrizes, sistemas) vão inteiros, antes de olhar palavra por palavra
    parts = DELIMITED.split(text)
    text = "".join(p if k % 2 else re.sub(r"\\begin\{(\w+\*?)\}.*?\\end\{\1\}", lambda m: f"\\({m.group(0)}\\)", p, flags=re.S)
                   for k, p in enumerate(parts))
    out = []
    for k, part in enumerate(DELIMITED.split(text)):
        if k % 2 or "\\" not in part:
            out.append(part)
            continue
        lines = []
        for line in part.split("\n"):
            toks = line.split(" ")
            is_cmd = [("\\" in t or "{" in t) for t in toks]
            mathy = [bool(t) and bool(MATHY.match(t)) and t.lower() not in WORDS and (len(t) <= 4 or c or re.search(r"[\d=+^_]", t))
                     for t, c in zip(toks, is_cmd)]
            # palavra entre espaçamentos do LaTeX ("\\, tal \\, que") faz parte da fórmula
            for j, t in enumerate(toks):
                if (j and toks[j - 1].endswith("\\,")) or (j + 1 < len(toks) and toks[j + 1].startswith("\\,")):
                    mathy[j] = True
            res, i = [], 0
            while i < len(toks):
                if not is_cmd[i]:
                    res.append(toks[i]); i += 1; continue
                a = i
                while a > 0 and mathy[a - 1] and (len(res) and res[-1] == toks[a - 1]):
                    a -= 1; res.pop()
                b = i
                while b + 1 < len(toks) and (mathy[b + 1] or is_cmd[b + 1]):
                    b += 1
                # chaves abertas ("\\large{massa \\over volume}") puxam as palavras até fechar
                while b + 1 < len(toks) and " ".join(toks[a:b + 1]).count("{") > " ".join(toks[a:b + 1]).count("}"):
                    b += 1
                span = " ".join(toks[a:b + 1])
                tail = re.search(r"[.,;:]+$", span)
                tail = tail.group(0) if tail and span.count("{") == span.count("}") else ""
                body = re.sub(r"\bIR\b", r"\\mathbb{R}", span[:len(span) - len(tail)] if tail else span)
                res.append(f"\\({body}\\){tail}")
                i = b + 1
            lines.append(" ".join(res))
        out.append("\n".join(lines))
    return "".join(out)


def download(urls):
    IMG.mkdir(parents=True, exist_ok=True)

    def one(url):
        target = IMG / local_name(url)
        if target.exists():
            return True
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "waterlearning-pipeline/0.1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                target.write_bytes(r.read())
            return True
        except Exception:
            return False

    with ThreadPoolExecutor(8) as ex:
        ok = list(ex.map(one, sorted(urls)))
    return {u for u, good in zip(sorted(urls), ok) if not good}


def main():
    raw = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(SRC.glob("*.json"))]
    out, images, seen = [], set(), set()
    for item in raw:
        q, gab, subj = item["q"], item["gab"], item["subject"]
        if gab.get("anulada") or not gab.get("resposta"):
            continue
        letters = [o["key"].lower() for o in q["options"]]
        if gab["resposta"].lower() not in letters:
            continue
        used = set()
        stem = to_markdown(q["enunciado"], used)
        opts = [{"t": to_markdown(o["text"], used)} for o in q["options"]]
        for o in opts:  # alternativa que é só uma imagem
            m = re.fullmatch(r"!\[\]\(([^)]+)\)", o["t"])
            if m:
                o["t"], o["img"] = "", m.group(1)
        if not stem or any(not o["t"] and not o.get("img") for o in opts):
            continue
        key = norm(stem)[:240]
        if key in seen:
            continue
        seen.add(key)
        images |= used
        hint = (q.get("topico") or {}).get("nome") or ""
        # o tópico da API é curado por pessoas: vale mais que qualquer palavra-chave
        topic, sub = map_api_topic(hint, subj) if hint else (None, None)
        if not topic and item.get("topic"):  # matéria de concurso (qdq_fetch amplo) já diz o tópico
            topic = item["topic"]
        if not topic and subj in DEFAULT:
            topic, _ = best_topic(f"{hint} {hint} {hint}", subj)
            if not topic:
                topic, _ = best_topic(stem + " " + " ".join(o["t"] for o in opts), subj, DEFAULT[subj])
        if not topic:
            topic = classify_topic(stem + " " + " ".join(o["t"] for o in opts), subj, hint) or DEFAULT_TOPIC[subj]
        out.append({
            "id": f"espcex-{q['id']}", "s": subj, "e": item["label"], "y": q.get("ano") or 0, "t": topic,
            "d": DIFF.get(q.get("dificuldade"), 2), "d_src": q.get("dificuldade"), "k": "text", "stem": stem, "opts": opts,
            "ans": letters.index(gab["resposta"].lower()), "tags": [], "hint": hint, **({"u": sub} if sub else {}),
            "src": f"{item['label']} {q.get('ano') or ''} · {q.get('nomeProva') or ''}".strip(" ·"),
        })
    failed = download(images)
    if failed:
        out = [x for x in out if not any(local_name(u) in json.dumps(x) for u in failed)]
        print(f"{len(failed)} imagens não baixaram; questões afetadas removidas")
    write_out("qdq", out)


if __name__ == "__main__":
    main()
