"""Exame da OAB (1ª fase, 2010–2025) a partir do dataset aberto russ7/oab_exams_2011_2025_combined
(que junta eduagarcia/oab_exams com as provas mais novas). Baixe antes com hf_fetch.py.

A área de cada questão: nas provas de 2010–2014 o rótulo da fonte é confiável (as áreas vêm em blocos contíguos,
como na prova). Nas de 2014–2018 não há rótulo, e nas de 2018–2025 o rótulo é ruído (a questão de honorários
aparece como Direito Penal). Ali vale a posição na prova, que segue blocos fixos por área desde 2013,
combinada com as palavras-chave da área.
"""
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, topic_scores, write_out

SRC = RAW / "hf" / "oab" / "train-00000-of-00001.jsonl"
TRUSTED = {"ETHICS": "dir-etica", "PHILOSOPHY": "dir-filosofia", "PHILOSHOPY": "dir-filosofia", "CONSTITUTIONAL": "dir-constitucional",
           "HUMAN-RIGHTS": "dir-humanos", "INTERNATIONAL": "dir-internacional", "TAXES": "dir-tributario",
           "ADMINISTRATIVE": "dir-administrativo", "ENVIRONMENTAL": "dir-ambiental", "CIVIL": "dir-civil", "CHILDREN": "dir-eca",
           "CONSUMER": "dir-consumidor", "BUSINESS": "dir-empresarial", "CIVIL-PROCEDURE": "dir-processo-civil",
           "CRIMINAL": "dir-penal", "CRIMINAL-PROCEDURE": "dir-processo-penal", "LABOUR": "dir-trabalho",
           "LABOUR-PROCEDURE": "dir-processo-trabalho"}
# blocos da prova de 80 questões desde 2013 (Exame XI): área → (primeira, última)
BLOCKS = {"dir-etica": (1, 10), "dir-filosofia": (11, 12), "dir-constitucional": (13, 19), "dir-humanos": (20, 22),
          "dir-internacional": (23, 24), "dir-tributario": (25, 29), "dir-administrativo": (30, 34), "dir-ambiental": (35, 36),
          "dir-civil": (37, 43), "dir-eca": (44, 45), "dir-consumidor": (46, 47), "dir-empresarial": (48, 52),
          "dir-processo-civil": (53, 58), "dir-penal": (59, 64), "dir-processo-penal": (65, 69), "dir-trabalho": (70, 75),
          "dir-processo-trabalho": (76, 80)}


def area(text, number):
    scores = {t: s for t, s in topic_scores(text, "dir").items() if t in BLOCKS}
    for t, (lo, hi) in BLOCKS.items():
        if lo <= number <= hi:
            scores[t] += 4
        elif lo - 2 <= number <= hi + 2:
            scores[t] += 1.5  # as fronteiras mudam uma ou duas questões de uma prova para outra
    return max(scores, key=scores.get)


def stem_of(question, choices):
    """o enunciado da fonte repete as alternativas no fim ("... A) texto B) texto"); corta a partir do "A)" """
    first = re.escape(choices[0][:25].strip())
    m = re.search(r"\s\(?A\)\s*" + first, question)
    if not m:
        m = list(re.finditer(r"\s\(?A\)\s", question))
        m = m[-1] if m else None
    text = question[: m.start()] if m else question
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()


def main():
    out, seen, skipped = [], set(), collections.Counter()
    for line in open(SRC, encoding="utf-8"):
        r = json.loads(line)
        if r["id"] in seen:
            continue  # as provas de 2010–2018 aparecem duas vezes (os dois datasets de origem)
        seen.add(r["id"])
        choices = [re.sub(r"\s+", " ", t).strip() for t in r["choices"]["text"]]
        if r["nullified"] or len(choices) != 4 or not all(choices) or len(set(choices)) < 4:
            skipped["anulada ou alternativas"] += 1
            continue
        stem = stem_of(r["question"], choices)
        if len(stem) < 20:
            skipped["enunciado vazio"] += 1
            continue
        text = stem + " " + " ".join(choices)
        topic = TRUSTED.get(r["question_type"]) or area(text, r["question_number"])
        year = int(r["exam_year"])
        out.append({
            "id": f"oab-{r['id']}", "s": "dir", "e": "OAB", "y": year, "t": topic, "d": 2, "lvl": 2, "k": "text",
            "stem": stem, "opts": [{"t": c} for c in choices], "ans": r["answerKey"], "tags": [],
            "src": f"OAB {year}, 1ª fase, questão {r['question_number']}",
        })
    print("descartadas:", dict(skipped))
    print(collections.Counter(q["t"] for q in out).most_common())
    write_out("oab", out)


if __name__ == "__main__":
    main()
