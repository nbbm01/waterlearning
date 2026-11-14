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
from common import PUBLIC, RAW, best_topic, norm, write_out

SRC = RAW / "qdq" / "questions"
IMG = PUBLIC / "img" / "qdq"
DIFF = {"FACIL": 1, "MEDIO": 2, "DIFICIL": 3}
DEFAULT = {"mat": "mat-conjuntos-funcoes", "fis": "fis-dinamica", "his": "his-brasil-contemporaneo"}
IMG_TAG = re.compile(r'<img[^>]+src="([^"]+)"[^>]*>', re.I)


def local_name(url):
    ext = Path(url.split("?")[0]).suffix.lower() or ".png"
    return hashlib.sha1(url.encode()).hexdigest()[:16] + ext


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
    return wrap_math(re.sub(r"\n{3,}", "\n\n", text).strip())


DELIMITED = re.compile(r"(\\\(.*?\\\)|\\\[.*?\\\]|\$\$.*?\$\$|!\[\]\([^)]*\))", re.S)
MATHY = re.compile(r"^[\w().,;:=+\-*/<>|\[\]^_{}\\'!°]+$")
WORDS = {"e", "a", "o", "de", "da", "do", "em", "ou", "que", "os", "as", "se", "um", "uma", "é", "no", "na"}


def wrap_math(text):
    """envolve LaTeX solto em \\( \\): agrupa palavras vizinhas com cara de fórmula"""
    text = re.sub(r"(?<!\$)\$([^$\n]+?)\$(?!\$)", lambda m: f"\\({m.group(1)}\\)" if re.search(r"[\\^_{]", m.group(1)) else m.group(0), text)
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
        # o tópico da API é bem específico; o nome dele pesa mais que o texto da questão
        topic, score = best_topic(f"{hint} {hint} {hint}", subj)
        if not topic:
            topic, _ = best_topic(stem + " " + " ".join(o["t"] for o in opts), subj, DEFAULT[subj])
        out.append({
            "id": f"espcex-{q['id']}", "s": subj, "e": item["label"], "y": q.get("ano") or 0, "t": topic,
            "d": DIFF.get(q.get("dificuldade"), 2), "k": "text", "stem": stem, "opts": opts,
            "ans": letters.index(gab["resposta"].lower()), "tags": [],
            "src": f"{item['label']} {q.get('ano') or ''} · {q.get('nomeProva') or ''}".strip(" ·"),
        })
    failed = download(images)
    if failed:
        out = [x for x in out if not any(local_name(u) in json.dumps(x) for u in failed)]
        print(f"{len(failed)} imagens não baixaram; questões afetadas removidas")
    write_out("qdq", out)


if __name__ == "__main__":
    main()
