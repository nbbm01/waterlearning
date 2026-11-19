"""Importa o ENEM a partir do dataset aberto yunger7/enem-api (pipeline/raw/enem-api)."""
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import PUBLIC, RAW, classify_topic, norm, pick_subject, reject_scores, topic_scores, write_out

SRC = RAW / "enem-api" / "public"
IMG_OUT = PUBLIC / "img" / "enem"
URL = re.compile(r"https://enem\.dev/(\d{4})/questions/([^/]+)/([^)\s\"]+)")

# Dificuldade estimada por tópico (o dataset não traz o parâmetro TRI); o texto longo sobe um degrau.
BASE = {
    "mat-aritmetica": 1, "mat-porcentagem": 1, "mat-estatistica": 1, "mat-grandezas-medidas": 1,
    "mat-log-exp": 3, "mat-combinatoria": 3, "mat-probabilidade": 3, "mat-complexos-polinomios": 3,
    "mat-trigonometria": 3, "fis-eletromagnetismo": 3, "fis-moderna": 3, "fis-hidrostatica": 3,
    "fis-cinematica": 1, "fis-optica": 2,
}


def localize(text, used):
    """troca URLs do enem.dev por caminhos locais e registra os arquivos usados"""
    def sub(m):
        year, q, name = m.groups()
        used.add((year, q, name))
        return f"data/img/enem/{year}-{q}-{name}"
    return URL.sub(sub, text or "")


def area_of(year, index, fallback):
    """área pela estrutura oficial da prova: o rótulo do dataset erra (a questão 109 de 2023, de polias, vem como Humanas;
    em 2010 as questões 103–135 de Linguagens vêm como Humanas). Em 2009: Natureza 1–45, Humanas 46–90. De 2010 a 2016:
    Humanas 1–45, Natureza 46–90. Até 2016, Linguagens 91–135 e Matemática 136–180. Desde 2017: Linguagens 1–45,
    Humanas 46–90, Natureza 91–135, Matemática 136–180."""
    order = (["ciencias-natureza", "ciencias-humanas", "linguagens", "matematica"] if year == 2009
             else ["ciencias-humanas", "ciencias-natureza", "linguagens", "matematica"] if year <= 2016
             else ["linguagens", "ciencias-humanas", "ciencias-natureza", "matematica"])
    return order[(index - 1) // 45] if 1 <= index <= 180 else fallback


def subject_of(d, text):
    disc = area_of(d["year"], d["index"], d["discipline"])
    if disc == "matematica":
        return "mat"
    if disc == "linguagens":
        return {"ingles": "ing", "espanhol": "esp"}.get(d.get("language") or "", "por")
    if disc == "ciencias-natureza":
        # Física com folga é Física (regra antiga, auditada). Nos demais casos as três disputam, com Química e Biologia
        # somando também as listas que já detectavam essas matérias; a Física só leva se passar das duas (o aço e o
        # desentupidor são Química, mesmo falando de calor e pressão), e a questão das polias deixa de ir para a Química.
        fis = sum(topic_scores(text, "fis").values())
        rej = reject_scores(text, ["quimica", "biologia"])
        if fis >= 3 and fis > 1.2 * max(rej.values()):
            return "fis"
        qui = sum(topic_scores(text, "qui").values()) + rej["quimica"]
        bio = sum(topic_scores(text, "bio").values()) + rej["biologia"]
        return "fis" if fis > max(qui, bio) else ("qui" if qui >= bio else "bio")
    if disc == "ciencias-humanas":
        his = sum(topic_scores(text, "his").values())
        rej = reject_scores(text, ["geografia", "filosofia", "sociologia"])
        nt = norm(text)
        if re.search(r"historiador|historiograf|seculo (xv|xvi|xvii|xviii|xix)\b", nt):
            his += 2
        return "his" if his >= 3 and his > 1.1 * max(rej.values()) else pick_subject(text, ["his", "geo", "fil", "soc"])
    return None


def difficulty(topic, text, seed):
    d = BASE.get(topic, 2)
    if len(text) > 1100:
        d += 1
    elif len(text) < 350 and seed % 3 == 0:
        d -= 1
    return max(1, min(3, d))


def main():
    used, out, seen = set(), [], set()
    for f in sorted(SRC.glob("*/questions/*/details.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        alts = d.get("alternatives") or []
        if len(alts) != 5 or not d.get("correctAlternative"):
            continue
        ctx, intro = d.get("context") or "", d.get("alternativesIntroduction") or ""
        if "broken-image" in json.dumps(d) or any(not (a.get("text") or "").strip() and not a.get("file") for a in alts):
            continue  # item incompleto no dataset
        plain = ctx + "\n" + intro + "\n" + "\n".join(a.get("text") or "" for a in alts)
        subj = subject_of(d, plain)
        if not subj:
            continue
        key = norm(plain)[:300]
        if key in seen:  # reaplicações repetem itens
            continue
        seen.add(key)
        topic = classify_topic(plain, subj)
        stem = localize(ctx, used)
        if intro:
            stem = (stem + "\n\n" + intro).strip()
        opts = []
        for a in alts:
            o = {"t": a.get("text") or ""}
            if a.get("file"):
                o["img"] = localize(a["file"], used)
            opts.append(o)
        # inglês e espanhol dividem o número da questão na prova
        qid = f"enem-{d['year']}-{d['index']}" + (f"-{d['language']}" if d.get("language") else "")
        out.append({
            "id": qid, "s": subj, "e": "ENEM", "y": d["year"], "t": topic,
            "d": difficulty(topic, plain, d["index"]), "k": "text", "stem": stem, "opts": opts,
            "ans": "ABCDE".index(d["correctAlternative"]), "tags": [],
            "src": f"ENEM {d['year']}, questão {d['index']}",
        })
    IMG_OUT.mkdir(parents=True, exist_ok=True)
    missing = 0
    for year, q, name in used:
        src = SRC / year / "questions" / q / name
        if src.exists():
            shutil.copyfile(src, IMG_OUT / f"{year}-{q}-{name}")
        else:
            missing += 1
    print(f"imagens: {len(used)} usadas, {missing} ausentes")
    write_out("enem", out)


if __name__ == "__main__":
    main()
