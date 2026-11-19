"""MMLU em português: o banco de Berkeley (questões de AP, GRE, USMLE, graduação) na tradução profissional da OpenAI
(openai/MMMLU, PT_BR) e as questões novas do MMLU-Pro (li-lab/MMLU-ProX, pt), que vêm de livros de STEM,
TheoremQA e SciBench. Do MMLU-Pro entram só as que não são do MMLU original, que já está aqui.

O MMLU-Pro tem 10 alternativas; ficam a certa e 4 distratores sorteados de forma fixa (5, como nas provas
brasileiras e nas teclas 1–5). Baixe antes com hf_fetch.py.
"""
import collections
import csv
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, classify_topic, write_out

MMMLU = RAW / "hf" / "mmmlu" / "mmlu_PT-BR.csv"
PRO = [RAW / "hf" / "mmlupx" / f"{s}-00000-of-00001.jsonl" for s in ("test", "validation")]

# assunto do MMLU → (matéria, tópico fixo ou None = palavras-chave, nível, nome em português)
SUBJECTS = {
    "abstract_algebra": ("mat", "mat-superior", 3, "Álgebra Abstrata"),
    "anatomy": ("med", "med-basicas", 2, "Anatomia"),
    "astronomy": ("fis", "fis-astronomia", 2, "Astronomia"),
    "business_ethics": ("eco", "eco-etica-negocios", 2, "Ética Empresarial"),
    "clinical_knowledge": ("med", None, 2, "Conhecimento Clínico"),
    "college_biology": ("bio", None, 3, "Biologia (graduação)"),
    "college_chemistry": ("qui", None, 3, "Química (graduação)"),
    "college_computer_science": ("com", None, 3, "Computação (graduação)"),
    "college_mathematics": ("mat", "mat-superior", 3, "Matemática (graduação)"),
    "college_medicine": ("med", None, 3, "Medicina (graduação)"),
    "college_physics": ("fis", None, 3, "Física (graduação)"),
    "computer_security": ("com", "com-redes-seguranca", 2, "Segurança da Informação"),
    "conceptual_physics": ("fis", None, 2, "Física Conceitual"),
    "econometrics": ("eco", "eco-econometria", 3, "Econometria"),
    "electrical_engineering": ("com", "com-eletrica", 3, "Engenharia Elétrica"),
    "elementary_mathematics": ("mat", None, 1, "Matemática Elementar"),
    "formal_logic": ("fil", "fil-logica", 3, "Lógica Formal"),
    "global_facts": ("ger", "ger-dados", 2, "Fatos Globais"),
    "high_school_biology": ("bio", None, 2, "Biologia (ensino médio)"),
    "high_school_chemistry": ("qui", None, 2, "Química (ensino médio)"),
    "high_school_computer_science": ("com", None, 2, "Computação (ensino médio)"),
    "high_school_european_history": ("his", None, 2, "História da Europa"),
    "high_school_geography": ("geo", None, 2, "Geografia (ensino médio)"),
    "high_school_government_and_politics": ("soc", "soc-politica", 2, "Governo e Política"),
    "high_school_macroeconomics": ("eco", "eco-macro", 2, "Macroeconomia"),
    "high_school_mathematics": ("mat", None, 2, "Matemática (ensino médio)"),
    "high_school_microeconomics": ("eco", "eco-micro", 2, "Microeconomia"),
    "high_school_physics": ("fis", None, 2, "Física (ensino médio)"),
    "high_school_psychology": ("psi", None, 2, "Psicologia (ensino médio)"),
    "high_school_statistics": ("mat", "mat-estatistica", 2, "Estatística"),
    "high_school_us_history": ("his", "his-eua", 2, "História dos EUA"),
    "high_school_world_history": ("his", None, 2, "História Mundial"),
    "human_aging": ("med", "med-geriatria", 2, "Envelhecimento Humano"),
    "human_sexuality": ("psi", None, 2, "Sexualidade Humana"),
    "international_law": ("dir", "dir-internacional", 3, "Direito Internacional"),
    "jurisprudence": ("dir", "dir-filosofia", 3, "Teoria do Direito"),
    "logical_fallacies": ("fil", "fil-logica", 2, "Falácias Lógicas"),
    "machine_learning": ("com", "com-ia", 3, "Aprendizado de Máquina"),
    "management": ("eco", "eco-administracao", 2, "Administração"),
    "marketing": ("eco", "eco-marketing", 2, "Marketing"),
    "medical_genetics": ("med", "med-patologia-genetica", 2, "Genética Médica"),
    "miscellaneous": ("ger", "ger-gerais", 2, "Conhecimentos Gerais"),
    "moral_disputes": ("fil", "fil-etica", 2, "Dilemas Morais"),
    "nutrition": ("sau", "sau-nutricao", 2, "Nutrição"),
    "philosophy": ("fil", None, 2, "Filosofia"),
    "prehistory": ("his", "his-antiguidade", 2, "Pré-História"),
    "professional_accounting": ("eco", "eco-contabilidade", 3, "Contabilidade (exame profissional)"),
    "professional_law": ("dir", "dir-eua", 3, "Direito (Bar Exam dos EUA)"),
    "professional_medicine": ("med", None, 3, "Medicina (USMLE)"),
    "professional_psychology": ("psi", None, 3, "Psicologia (exame profissional)"),
    "public_relations": ("eco", "eco-marketing", 2, "Relações Públicas"),
    "security_studies": ("geo", "geo-geopolitica", 3, "Estudos de Segurança"),
    "sociology": ("soc", None, 2, "Sociologia"),
    "us_foreign_policy": ("his", "his-eua", 2, "Política Externa dos EUA"),
    "virology": ("med", "med-microbiologia", 2, "Virologia"),
    "world_religions": ("fil", "fil-estetica-religiao", 2, "Religiões do Mundo"),
    # moral_scenarios fica de fora: são pares de cenários sobre "padrões morais dos EUA em 2020", não questões de prova
}
PRO_SUBJECTS = {"chemistry": ("qui", "Química"), "engineering": ("com", "Engenharia"), "physics": ("fis", "Física"),
                "business": ("eco", "Negócios"), "math": ("mat", "Matemática"), "biology": ("bio", "Biologia"),
                "economics": ("eco", "Economia"), "psychology": ("psi", "Psicologia"), "computer science": ("com", "Computação"),
                "health": ("med", "Saúde"), "law": ("dir", "Direito"), "philosophy": ("fil", "Filosofia"),
                "history": ("his", "História"), "other": ("ger", "Conhecimentos Gerais")}
PRO_SOURCE = {"stemez": "livros de STEM", "theoremQA": "TheoremQA", "scibench": "SciBench"}


def clean(text):
    text = re.sub(r"[ \t ]+", " ", (text or "").replace("\r", ""))
    text = re.sub(r" *\n *", "\n", text)
    # "$$" do texto viraria fórmula no site
    return re.sub(r"\n{3,}", "\n\n", text).replace("$$", "$ $").strip()


def valid(stem, opts):
    return len(stem) >= 8 and all(opts) and len({o.lower() for o in opts}) == len(opts)


def mmmlu(out, skipped):
    for row in csv.DictReader(open(MMMLU, encoding="utf-8")):
        spec = SUBJECTS.get(row["Subject"])
        if not spec:
            skipped["moral_scenarios"] += 1
            continue
        subj, topic, lvl, label = spec
        stem, opts = clean(row["Question"]), [clean(row[k]) for k in "ABCD"]
        if not valid(stem, opts) or row["Answer"] not in "ABCD":
            skipped["inválida"] += 1
            continue
        out.append({
            "id": f"mmlu-{row['Subject']}-{row['']}", "s": subj, "e": "MMLU", "y": None,
            "t": topic or classify_topic(stem + " " + " ".join(opts), subj, label), "d": lvl, "lvl": lvl, "k": "text",
            "stem": stem, "opts": [{"t": o} for o in opts], "ans": "ABCD".index(row["Answer"]), "tags": [row["Subject"]],
            "hint": label, "src": f"MMLU (Berkeley), {label}",
        })


def mmlu_pro(out, skipped):
    for path in PRO:
        for line in open(path, encoding="utf-8"):
            row = json.loads(line)
            if row["src"].startswith("ori_mmlu"):
                continue  # já entrou pelo MMMLU, com tradução humana
            spec = PRO_SUBJECTS.get(row["category"])
            if not spec:
                skipped[f"categoria {row['category']}"] += 1
                continue
            subj, label = spec
            opts = [clean(row.get(f"option_{i}")) for i in range(10)]
            idx = [i for i, o in enumerate(opts) if o and o != "N/A"]
            ans = row["answer_index"]
            if ans not in idx:
                skipped["inválida"] += 1
                continue
            rng = random.Random(f"mmlupro-{row['question_id']}")
            keep = sorted([ans] + rng.sample([i for i in idx if i != ans], min(4, len(idx) - 1)))
            stem, chosen = clean(row["question"]), [opts[i] for i in keep]
            if not valid(stem, chosen):
                skipped["inválida"] += 1
                continue
            origin = PRO_SOURCE.get(row["src"].split("-")[0], "MMLU-Pro")
            out.append({
                "id": f"mmlupro-{row['question_id']}", "s": subj, "e": "MMLU-Pro", "y": None,
                "t": classify_topic(stem + " " + " ".join(chosen), subj, label), "d": 3, "lvl": 3, "k": "text",
                "stem": stem, "opts": [{"t": o} for o in chosen], "ans": keep.index(ans), "tags": [row["category"]],
                "hint": label, "src": f"MMLU-Pro ({origin}), {label}",
            })


def main():
    out, skipped = [], collections.Counter()
    mmmlu(out, skipped)
    mmlu_pro(out, skipped)
    print("descartadas:", dict(skipped))
    print(collections.Counter((q["e"], q["s"]) for q in out).most_common())
    write_out("mmlu", out)


if __name__ == "__main__":
    main()
