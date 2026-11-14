"""Importa o ENEM a partir do dataset aberto yunger7/enem-api (pipeline/raw/enem-api)."""
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import PUBLIC, RAW, best_topic, norm, reject_scores, topic_scores, write_out

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


def subject_of(d, text):
    disc = d["discipline"]
    if disc == "matematica":
        return "mat"
    if disc == "ciencias-natureza":
        fis = sum(topic_scores(text, "fis").values())
        rej = reject_scores(text, ["quimica", "biologia"])
        return "fis" if fis >= 3 and fis > 1.2 * max(rej.values()) else None
    if disc == "ciencias-humanas":
        his = sum(topic_scores(text, "his").values())
        rej = reject_scores(text, ["geografia", "filosofia", "sociologia"])
        nt = norm(text)
        if re.search(r"historiador|historiograf|seculo (xv|xvi|xvii|xviii|xix)\b", nt):
            his += 2
        return "his" if his >= 3 and his > 1.1 * max(rej.values()) else None
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
        if d.get("language") or len(alts) != 5 or not d.get("correctAlternative"):
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
        default = {"mat": "mat-aritmetica", "fis": "fis-energia", "his": "his-brasil-contemporaneo"}[subj]
        topic, _ = best_topic(plain, subj, default)
        stem = localize(ctx, used)
        if intro:
            stem = (stem + "\n\n" + intro).strip()
        opts = []
        for a in alts:
            o = {"t": a.get("text") or ""}
            if a.get("file"):
                o["img"] = localize(a["file"], used)
            opts.append(o)
        qid = f"enem-{d['year']}-{d['index']}"
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
