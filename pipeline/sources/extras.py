"""Provas menores de datasets abertos: ENEM 2024 (maritaca-ai/enem), ENADE (INEP, via northern-64bit),
POSCOMP (maritaca-ai/poscomp) e os Exames Nacionais do ensino secundário de Portugal (amalia-llm/pt_exams).
Baixe antes com hf_fetch.py.
"""
import ast
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, classify_topic, needs_figure, pick_subject, write_out

HF = RAW / "hf"
OPT_PREFIX = re.compile(r"^\s*\(?[A-Ea-e]\)\s*")


def clean(text):
    text = re.sub(r"[ \t ]+", " ", (text or "").replace("\r", ""))
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).replace("$$", "$ $").strip()


def as_list(value):
    return value if isinstance(value, list) else ast.literal_eval(value)


def ok(stem, opts):
    return len(stem) >= 20 and 4 <= len(opts) <= 5 and all(opts) and len(set(opts)) == len(opts) and not needs_figure(stem)


def enem2024(out, skipped):
    for line in open(HF / "enem24" / "2024.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if r["IU"] in (True, "True"):  # depende de imagem, que o dataset não traz
            skipped["ENEM 2024 com imagem"] += 1
            continue
        n = int(r["id"].split("_")[1])
        stem = clean(re.sub(r"^#+\s*", "", r["question"], flags=re.M))
        opts = [clean(o) for o in as_list(r["alternatives"])]
        if not ok(stem, opts) or r["label"] not in "ABCDE":
            skipped["ENEM 2024 inválida"] += 1
            continue
        text = stem + " " + " ".join(opts)
        if n <= 5:
            subj = pick_subject(text, ["ing", "esp"])
        elif n <= 45:
            subj = "por"
        elif n <= 90:
            subj = pick_subject(text, ["his", "geo", "fil", "soc"])
        elif n <= 135:
            subj = pick_subject(text, ["fis", "qui", "bio"])
        else:
            subj = "mat"
        out.append({"id": f"enem-2024-{n}", "s": subj, "e": "ENEM", "y": 2024, "t": classify_topic(text, subj), "d": 2, "k": "text",
                    "stem": stem, "opts": [{"t": o} for o in opts], "ans": "ABCDE".index(r["label"]), "tags": [],
                    "src": f"ENEM 2024, questão {n}"})


# curso do ENADE → matéria
ENADE = {"Medicina": "med", "Direito": "dir", "Letras": "por", "Relações Internacionais": "geo", "Zootecnia": "sau", "Teologia": "fil",
         "Agronomia": "geo", "Serviços Social": "sau", "Com Social Jornalismo": "soc", "Turismo": "eco", "Nutrição": "sau",
         "MEDICINA VETERINÁRIA": "sau", "Computação": "com", "Odontologia": "sau", "Tecnologia em Gestão Hospitalar": "eco",
         "Tecnologia em Gestão Financeira": "eco", "CIÊNCIAS SOCIAIS": "soc", "TECNOLOGIA EM SANEAMENTO AMBIENTAL": "geo",
         "Tecnologia em Alimentos": "qui", "Tecnologia em Radiologia": "sau", "Ciencias Contabeis": "eco", "História": "his"}


def enade(out, skipped):
    for r in json.load(open(HF / "enade" / "ENADE_Brazilian_national_university_examination_MCQ.json", encoding="utf-8")):
        opts = [clean(o) for o in as_list(r["options"])]
        # algumas linhas trazem as afirmativas (I, II, III...) no lugar das alternativas
        if any(re.match(r"^(I{1,3}|IV|V)\s*[.)–-]", o) for o in opts):
            skipped["ENADE sem alternativas"] += 1
            continue
        stem = clean(r["question"])
        ans = int(r["answer"]) - 1
        subj = ENADE.get(r["category_original_lang"])
        if not subj or not ok(stem, opts) or not 0 <= ans < len(opts):
            skipped["ENADE inválida"] += 1
            continue
        found = re.search(r"(?:19|20)\d{2}", r["file_name"]) or re.search(r"(?:19|20)\d{2}", r.get("source") or "")
        year = int(found.group()) if found else None
        out.append({"id": f"enade-{r['file_name'][:-4]}-{r['original_question_num']}", "s": subj, "e": "ENADE", "y": year,
                    "t": classify_topic(stem + " " + " ".join(opts), subj, r["category_original_lang"]), "d": 2, "lvl": 2, "k": "text",
                    "stem": stem, "opts": [{"t": o} for o in opts], "ans": ans, "tags": [r["category_original_lang"]],
                    "src": f"ENADE {year or ''}, {r['category_original_lang'].capitalize()}, questão {r['original_question_num']}".replace(" ,", ",")})


def poscomp(out, skipped):
    for line in open(HF / "poscomp" / "train-00000-of-00001.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if r["has_associated_images"] in (True, "True") or r["IU"] in (True, "True"):
            skipped["POSCOMP com imagem"] += 1
            continue
        stem = clean(r["question"])
        opts = [clean(OPT_PREFIX.sub("", o)) for o in as_list(r["alternatives"])]
        if not ok(stem, opts) or r["answer"] not in "ABCDE"[: len(opts)]:
            skipped["POSCOMP inválida"] += 1
            continue
        _, year, num = r["id"].split("_")
        out.append({"id": f"poscomp-{year}-{num}", "s": "com", "e": "POSCOMP", "y": int(year),
                    "t": classify_topic(stem + " " + " ".join(opts), "com"), "d": 3, "lvl": 3, "k": "text",
                    "stem": stem, "opts": [{"t": o} for o in opts], "ans": "ABCDE".index(r["answer"]), "tags": [],
                    "src": f"POSCOMP {year}, questão {num}"})


PT_SUBJECTS = {"Geography": "geo", "Philosophy": "fil", "Portuguese": "por", "Mathematics A": "mat", "History A": "his"}


def portugal(out, skipped):
    for i, r in enumerate(json.load(open(HF / "ptexams" / "all.json", encoding="utf-8"))):
        subj = PT_SUBJECTS.get(r["subject"]) or pick_subject(r["question"], ["bio", "geo"])  # "Bio_Geo": Biologia e Geologia
        stem, opts = clean(r["question"]), [clean(o) for o in r["choices"]]
        if not ok(stem, opts) or not 0 <= r["answer"] < len(opts):
            skipped["Portugal inválida"] += 1
            continue
        out.append({"id": f"ptexame-{r['year']}-{i}", "s": subj, "e": "Exame Nacional (Portugal)", "y": r["year"],
                    "t": classify_topic(stem + " " + " ".join(opts), subj), "d": 2, "lvl": 2, "k": "text",
                    "stem": stem, "opts": [{"t": o} for o in opts], "ans": r["answer"], "tags": [r["subject"]],
                    "src": f"Exame Nacional de Portugal {r['year']}, {r['phase'].lower()}, {r['subject']}"})


def main():
    out, skipped = [], collections.Counter()
    for fn in (enem2024, enade, poscomp, portugal):
        fn(out, skipped)
    print("descartadas:", dict(skipped))
    print(collections.Counter(q["e"] for q in out).most_common(), collections.Counter(q["s"] for q in out).most_common())
    write_out("extras", out)


if __name__ == "__main__":
    main()
