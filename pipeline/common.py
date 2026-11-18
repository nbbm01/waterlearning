"""Utilidades compartilhadas pelos importadores."""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPE = ROOT / "pipeline"
RAW = PIPE / "raw"
OUT = PIPE / "out"
PUBLIC = ROOT / "public" / "data"
BOOKS = Path.home() / "Downloads" / "conteudo"

TAXONOMY = json.loads((PIPE / "taxonomy.json").read_text(encoding="utf-8"))
MILITARY = {"ITA", "IME", "AFA", "EFOMM", "EsPCEx", "EN", "CN", "EEAR", "ESA", "EPCAr", "CMRJ", "APMBB", "EAM", "CFO-BM"}

# Elo inicial da questão por nível de dificuldade
RATING = {1: 800, 2: 1050, 3: 1300}  # quem começa (Elo 1000) acerta ~76% do nível 1


def norm(text):
    """minúsculas, sem acento, espaços colapsados"""
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text.lower())


_PATTERNS = {}


def _pattern(kw):
    p = _PATTERNS.get(kw)
    if p is None:
        # palavra-chave casa como prefixo de palavra
        p = _PATTERNS[kw] = re.compile((r"(?<![a-z0-9])" if kw[0].isalnum() else "") + re.escape(kw))
    return p


def _score(ntext, kws):
    total = 0
    for kw in kws:
        if kw not in ntext:  # filtro barato: a maioria das palavras-chave nem aparece no texto
            continue
        hits = len(_pattern(kw).findall(ntext))
        if hits:
            total += min(hits, 3) * (2 if " " in kw.strip() else 1)  # termos compostos valem mais
    return total


def topic_scores(text, subject):
    ntext = norm(text)
    subj = next(s for s in TAXONOMY["subjects"] if s["id"] == subject)
    return {t["id"]: _score(ntext, t["kw"]) for t in subj["topics"]}


def pick_subject(text, candidates):
    """matéria mais provável entre as candidatas, pela soma das palavras-chave dos tópicos de cada uma"""
    scores = {s: sum(topic_scores(text, s).values()) for s in candidates}
    return max(scores, key=scores.get)


# tópico de quem não casou com nada: o mais genérico da matéria
DEFAULT_TOPIC = {"mat": "mat-aritmetica", "fis": "fis-energia", "his": "his-brasil-contemporaneo", "qui": "qui-inorganica",
                 "bio": "bio-ecologia", "geo": "geo-globalizacao", "fil": "fil-etica", "soc": "soc-contemporanea",
                 "por": "por-interpretacao", "ing": "ing-interpretacao", "esp": "esp-interpretacao", "dir": "dir-civil",
                 "med": "med-preventiva", "sau": "sau-saude-coletiva", "psi": "psi-clinica", "eco": "eco-administracao",
                 "com": "com-programacao", "ger": "ger-gerais"}


def classify_topic(text, subject, hint=""):
    """tópico pelo texto; a pista da fonte (tags, área, capítulo) pesa triplo"""
    topic, _ = best_topic(f"{hint} " * 3 + text if hint else text, subject, DEFAULT_TOPIC[subject])
    return topic


# enunciado que depende de figura que a fonte não trouxe (o dataset é "sem imagem")
NEEDS_FIGURE = re.compile(r"\b(figura|grafico|imagem|charge|tirinha|tira|cartum|fotografia|foto|ilustracao|esquema|diagrama|mapa|"
                          r"quadrinho|cartaz|infografico|gravura|pintura|tela)\s+(a seguir|abaixo|acima|ao lado|seguinte|apresentad|mostrad|representad)"
                          r"|\b(observe|analise|veja|considere|examine|leia) (a|o|as|os) (figura|grafico|imagem|charge|tirinha|cartum|fotografia|foto|"
                          r"ilustracao|esquema|diagrama|mapa|quadrinho|cartaz|infografico|gravura|pintura|tela)s?\b"
                          r"|\b(na|no|nas|nos|da|do|pela|pelo) (figura|grafico|imagem|charge|tirinha|cartum|fotografia|ilustracao|esquema|mapa|cartaz|infografico)s?\b"
                          # casos clínicos: "uma fotomicrografia é mostrada", "(mostradas na imagem)", "o ECG abaixo"
                          r"|\b(e|sao|esta|estao|foi|foram) (mostrad|exibid|apresentad)[oa]s?( abaixo| a seguir| ao lado)?\s*[.,:;)]"
                          r"|\bmostrad[oa]s? (abaixo|a seguir|ao lado)|\b(fotomicrografia|micrografia|eletrocardiograma|ecg|radiografia|tomografia)"
                          r" (abaixo|a seguir|ao lado|mostrad|exibid)")


def needs_figure(text):
    return bool(NEEDS_FIGURE.search(norm(text)))


def reject_scores(text, areas):
    ntext = norm(text)
    return {a: _score(ntext, TAXONOMY["reject"][a]) for a in areas}


def best_topic(text, subject, default=None):
    scores = topic_scores(text, subject)
    tid, sc = max(scores.items(), key=lambda kv: kv[1])
    if sc > 0:
        return tid, sc
    # palavras genéricas só decidem quando nenhuma específica casou
    ntext = norm(text)
    subj = next(s for s in TAXONOMY["subjects"] if s["id"] == subject)
    weak = {t["id"]: _score(ntext, t.get("weak", [])) for t in subj["topics"]}
    tid, sc = max(weak.items(), key=lambda kv: kv[1])
    return (tid, 0) if sc > 0 else (default, 0)


def subtopic(text, subject, topic, hint=""):
    """(tópico, subtópico) mais prováveis. A pista (subtítulo do livro, tópico da API) pesa triplo.

    Sem pista, a questão pode mudar de tópico quando um subtópico de outro tópico casa com
    muito mais força (ex.: "equação do 1º grau" classificada antes como Aritmética)."""
    ntext = norm(f"{hint} " * 3 + text)
    subj = next(s for s in TAXONOMY["subjects"] if s["id"] == subject)
    scores = {(t["id"], sb["id"]): _score(ntext, sb["kw"]) + 2 * _score(norm(hint), [norm(a) for a in sb["aliases"]])
              for t in subj["topics"] for sb in t.get("subs", [])}
    own = {k: v for k, v in scores.items() if k[0] == topic}
    best_own = max(own.items(), key=lambda kv: kv[1], default=(None, 0))
    if not hint and best_own[0]:
        # sem pista da fonte, só classifica com folga: questão "nada a ver" num subtópico estraga o treino
        second = max((v for k, v in own.items() if k != best_own[0]), default=0)
        if best_own[1] < 3 or best_own[1] < 1.5 * second:
            best_own = (None, 0)
    if not hint:
        best_any = max(scores.items(), key=lambda kv: kv[1], default=(None, 0))
        if best_any[0] and best_any[0][0] != topic and best_any[1] >= 6 and best_any[1] >= 2 * best_own[1]:
            return best_any[0]
    return (topic, best_own[0][1]) if best_own[0] and best_own[1] > 0 else (topic, None)


def write_out(name, questions):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(questions, ensure_ascii=False), encoding="utf-8")
    print(f"{name}: {len(questions)} questões")
