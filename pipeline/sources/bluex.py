"""FUVEST (USP) e UNICAMP 2018–2024 a partir do dataset aberto BLUEX (portuguese-benchmark-datasets/BLUEX)."""
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from books import difficulty
from common import PUBLIC, RAW, best_topic, write_out

SRC = RAW / "bluex-data"
SUBJECTS = {"mathematics": "mat", "physics": "fis", "history": "his"}
EXAMS = {"USP": "FUVEST", "UNICAMP": "UNICAMP"}
DEFAULT = {"mat": "mat-aritmetica", "fis": "fis-energia", "his": "his-brasil-contemporaneo"}
OPT_PREFIX = re.compile(r"^\s*\(?[a-eA-E]\)\s*")


def unwrap(text):
    """o PDF quebra linha no meio da frase; mantém só quebras de parágrafo"""
    text = re.sub(r"[ \t]+", " ", text.replace("\r", ""))
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"(?<![.:;?!”\"])\n(?!\n)(?=\S)", " ", text)
    text = re.sub(r" {2,}", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def local_image(rel, used):
    used.add(rel)
    return "data/img/bluex/" + rel.removeprefix("imgs/").replace("/", "-")


def main():
    out, used = [], set()
    files = sorted(SRC.glob("questions/*/*/*.json"))
    by_exam = {}
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        subj = next((SUBJECTS[s] for s in d["subject"] if s in SUBJECTS), None)
        if not subj or not d.get("answer") or d["answer"] not in "ABCDE":
            continue
        imgs = d.get("associated_images") or []
        stem = unwrap(d["question"])
        stem = re.sub(r"\[IMAGE (\d+)\]", lambda m: f"\n\n![]({local_image(imgs[int(m.group(1))], used)})\n\n"
                      if int(m.group(1)) < len(imgs) else "", stem)
        # imagens sem marcador no texto vão para o início do enunciado
        unplaced = [i for i in imgs if local_image(i, set()) not in stem]
        if d["alternatives_type"] != "images" and unplaced:
            stem = "\n\n".join(f"![]({local_image(i, used)})" for i in unplaced) + "\n\n" + stem
        opts = []
        for k, alt in enumerate(d["alternatives"]):
            if d["alternatives_type"] == "images":
                src = alt if alt.startswith("imgs/") else (imgs[k] if k < len(imgs) else "")
                if not src:
                    opts = []
                    break
                opts.append({"t": "", "img": local_image(src, used)})
            else:
                opts.append({"t": unwrap(OPT_PREFIX.sub("", alt))})
        if len(opts) < 4 or any(not o["t"] and not o.get("img") for o in opts):
            continue
        exam = EXAMS[d["id"].split("_")[0]]
        year = int(d["id"].split("_")[1])
        plain = stem + " " + " ".join(o["t"] for o in opts)
        topic, _ = best_topic(plain, subj, DEFAULT[subj])
        q = {"id": "bluex-" + d["id"].lower(), "s": subj, "e": exam, "y": year, "t": topic, "k": "text",
             "stem": stem, "opts": opts, "ans": "ABCDE".index(d["answer"]), "tags": [],
             "src": f"{exam} {year}, questão {d['number']}"}
        by_exam.setdefault((exam, year, subj), []).append((d["number"], q))
    for group in by_exam.values():
        group.sort(key=lambda t: t[0])
        for pos, (_, q) in enumerate(group):
            # nas provas da FUVEST e UNICAMP a ordem não segue a dificuldade: usa o tamanho do texto como sinal
            q["d"] = difficulty(1 if len(q["stem"]) < 900 else 2, 3, "")
            out.append(q)
    dest = PUBLIC / "img" / "bluex"
    dest.mkdir(parents=True, exist_ok=True)
    for rel in used:
        shutil.copyfile(SRC / rel, dest / rel.removeprefix("imgs/").replace("/", "-"))
    write_out("bluex", out)


if __name__ == "__main__":
    main()
