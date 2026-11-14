"""FUVEST 2006–2017, 1ª fase (prova V + gabarito oficial do acervo fuvest.br). 2018+ vem do BLUEX."""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from books import difficulty
from common import RAW, best_topic, reject_scores, topic_scores, write_out
from exam_pdf import crop_questions, option_count, segment_columns

DIR = RAW / "fuvest"
START = re.compile(r"^(\d{2})(?:\s+\S|$)")
DEFAULT = {"mat": "mat-aritmetica", "fis": "fis-energia", "his": "his-brasil-contemporaneo"}
OTHERS = ["quimica", "biologia", "geografia", "filosofia", "sociologia", "linguagens"]


def answer_key(pdf):
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    text = text.replace("‐", "-")
    keys = {int(n): "ABCDE".index(a) for n, a in re.findall(r"\bV (\d{2})\s*-\s*([A-E])\b", text)}
    if not keys:  # 2006–2007: "RESPOSTA  GRUPO V  GRUPO K ..."
        keys = {int(n): "ABCDE".index(a) for a, n in re.findall(r"\b([A-E])\s+(\d{2})\s+\d{2}\s+\d{2}\s+\d{2}\s+\d{2}", text)}
    return keys


def subject_of(text):
    """a 1ª fase mistura as matérias sem rótulo; decide pelo vocabulário"""
    own = {s: sum(topic_scores(text, s).values()) for s in ("mat", "fis", "his")}
    other = max(reject_scores(text, OTHERS).values())
    subj, score = max(own.items(), key=lambda kv: kv[1])
    numeric = len(re.findall(r"\d", text)) / max(len(text), 1)
    if subj == "his" and re.search(r"(?i)historiador|s[ée]culo|colonial|imp[ée]rio|revolu", text):
        score += 3
    if subj == "mat" and numeric > 0.04:
        score += 2
    return subj if score >= 4 and score > 1.15 * other else None


def main():
    out = []
    for year in range(2006, 2018):
        prova, gab = DIR / f"fuvest_{year}_1fase_prova_V.pdf", DIR / f"fuvest_{year}_1fase_prova_gab.pdf"
        if not prova.exists() or not gab.exists():
            continue
        keys = answer_key(gab)
        qs = segment_columns(prova, START)
        chosen = {}
        for num, q in qs.items():
            subj = subject_of(q["text"]) if num in keys and q["segs"] else None
            if subj:
                chosen[num] = (subj, q)
        imgs = crop_questions(prova, {n: q for n, (_, q) in chosen.items()}, f"fuvest{year}", "fuvest")
        for num, (subj, q) in sorted(chosen.items()):
            topic, _ = best_topic(q["text"], subj, DEFAULT[subj])
            out.append({
                "id": f"fuvest-{year}-{num}", "s": subj, "e": "FUVEST", "y": year, "t": topic,
                "d": difficulty(1 if len(q["text"]) < 700 else 2, 3, "FUVEST"), "k": "image", "opts": [],
                "n": max(option_count(q["text"].replace("\n", " ")), keys[num] + 1), "ans": keys[num],
                "imgs": imgs[num], "tags": [], "raw": q["text"], "src": f"FUVEST {year}, 1ª fase, questão {num} (prova V)",
            })
        print(f"FUVEST {year}: {len(qs)} questões na prova, {len(keys)} no gabarito, {len(chosen)} de Mat/Fís/Hist")
    write_out("fuvest", out)


if __name__ == "__main__":
    main()
