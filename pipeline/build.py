"""Junta pipeline/out/*.json + curadoria e gera public/data (index, chunks, meta, teoria)."""
import collections
import hashlib
import re
import json
import shutil

from common import MILITARY, OUT, PIPE, PUBLIC, RATING, TAXONOMY, subtopic

CHUNK = 60
F_COMMENTED, F_CLASSIC, F_MILITARY, F_IMAGE = 1, 2, 4, 8
# deslocamento de Elo por banca: provas mais seletivas valem mais
EXAM_OFFSET = {"ITA": 300, "IME": 300, "EN": 150, "AFA": 100, "EFOMM": 100, "EsPCEx": 100, "FUVEST": 100, "UNICAMP": 100}


def load():
    questions = {}
    for f in sorted(OUT.glob("*.json")):
        for q in json.loads(f.read_text(encoding="utf-8")):
            questions[q["id"]] = q
    # curadoria: transcrições em KaTeX, resoluções e correções, por id
    for f in sorted((PIPE / "curated").glob("*.json")):
        for qid, patch in json.loads(f.read_text(encoding="utf-8")).items():
            if qid in questions:
                questions[qid].update(patch)
    return list(questions.values())


def classify(q):
    """subtópico a partir do texto (enunciado, texto extraído do recorte) e da pista da fonte"""
    text = q.get("raw") or (q.get("stem") or "") + " " + " ".join(o.get("t", "") for o in q.get("opts", []))
    if q.get("u"):  # a fonte já trouxe o subtópico (tópico da API, capítulo do livro, gerador)
        # ...mas um capítulo de "equação" às vezes traz inequações: o texto decide
        if q["u"] in ("mat-equacao-1grau", "mat-equacao-2grau") and re.search(r"[<>≤≥⩽⩾≦≧]|\\(le|ge|lt|gt|leq|geq|leqslant|geqslant)\b|inequa", text):
            q["u"] = "mat-inequacoes"
        return
    text = q.get("raw") or (q.get("stem") or "") + " " + " ".join(o.get("t", "") for o in q.get("opts", []))
    q["t"], q["u"] = subtopic(text, q["s"], q["t"], q.get("hint") or "")


TOUGH = {"ITA", "IME"}
MILITARY_MID = {"EsPCEx", "EFOMM", "AFA", "EN", "EPCAr", "CN", "CMRJ", "EEAR"}
SELECTIVE = {"FUVEST", "UNICAMP"}


def calibrate(q):
    """dificuldade numa escala única, na lógica de um livro didático:
    1 = treino (conta direta), 2 = aplicação (problema, vestibular regional), 3 = vestibular exigente.
    A fonte só desempata dentro do nível da banca."""
    e, d = q["e"], q["d"]
    if e == "Waterlearning":  # o gerador já sabe se é treino ou problema
        return d
    if e in TOUGH:
        return 3
    if e in MILITARY_MID or e in SELECTIVE:
        return 3 if d >= 2 else 2
    if e == "Concursos":
        return 2 if d == 3 else 1
    if e == "ENEM":
        return d
    return max(2, d)  # questões de vestibular (inclusive as dos livros) nunca são "treino"


def main():
    qs = load()
    quarantine = PIPE / "quarantine.json"
    if quarantine.exists():  # fórmulas quebradas apontadas por audit_render.ts
        blocked = set(json.loads(quarantine.read_text(encoding="utf-8")))
        qs = [q for q in qs if q["id"] not in blocked]
    for q in qs:
        classify(q)
        q["d"] = calibrate(q)
    qs.sort(key=lambda q: (q["s"], q["e"], q["y"] or 0, q["id"]))

    # "Clássicas": tópicos que concentram mais questões dentro de cada matéria/banca
    freq = collections.Counter((q["s"], q["e"], q["t"]) for q in qs)
    classic = set()
    by_group = collections.defaultdict(list)
    for (s, e, t), n in freq.items():
        by_group[(s, e)].append((n, t))
    for (s, e), items in by_group.items():
        items.sort(reverse=True)
        for n, t in items[: max(1, round(len(items) * 0.3))]:
            classic.add((s, e, t))

    subjects = [{"id": s["id"], "name": s["name"],
                 "topics": [{"id": t["id"], "name": t["name"], "aliases": t["aliases"],
                             "subs": [{"id": sb["id"], "name": sb["name"], "aliases": sb["aliases"]} for sb in t.get("subs", [])]}
                            for t in s["topics"]]}
                for s in TAXONOMY["subjects"]]
    exams = sorted({q["e"] for q in qs})
    subj_ids = [s["id"] for s in subjects]
    topic_ids = [t["id"] for s in subjects for t in s["topics"]]
    sub_ids = [sb["id"] for s in subjects for t in s["topics"] for sb in t["subs"]]

    # a versão vai na URL dos blocos (?v=); uma aba com índice antigo percebe a troca e recarrega
    version = hashlib.sha1(json.dumps(qs, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:10]
    chunks_dir = PUBLIC / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    index = []
    for ci in range(0, len(qs), CHUNK):
        block = qs[ci: ci + CHUNK]
        cid = ci // CHUNK
        payload = {}
        for q in block:
            flags = 0
            if q.get("exp"):
                flags |= F_COMMENTED
            if (q["s"], q["e"], q["t"]) in classic:
                flags |= F_CLASSIC
            if q["e"] in MILITARY:
                flags |= F_MILITARY
            if q["k"] == "image":
                flags |= F_IMAGE
            rating = RATING[q["d"]] + EXAM_OFFSET.get(q["e"], 0)
            index.append([q["id"], subj_ids.index(q["s"]), exams.index(q["e"]), q["y"] or 0,
                          topic_ids.index(q["t"]), q["d"], flags, cid, rating, sub_ids.index(q["u"]) if q["u"] else -1])
            payload[q["id"]] = {k: q[k] for k in ("k", "stem", "opts", "ans", "n", "imgs", "exp", "src", "book") if q.get(k) is not None}
        (chunks_dir / f"{cid}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # sobrescreve no lugar e só remove blocos que sobraram (apagar a pasta confunde o servidor de dev)
    for stale in chunks_dir.iterdir():
        if stale.is_dir():
            shutil.rmtree(stale)
        elif not stale.stem.isdigit() or int(stale.stem) * CHUNK >= len(qs):
            stale.unlink()

    theory = {}
    for f in sorted((PIPE / "theory").glob("*.json")):
        theory.update(json.loads(f.read_text(encoding="utf-8")))
    cut = PIPE / "cutoffs.json"
    meta = {
        "subjects": subjects, "exams": exams, "military": sorted(MILITARY & set(exams)),
        "total": len(qs), "theory": theory, "version": version,
        "sims": json.loads(cut.read_text(encoding="utf-8")) if cut.exists() else {},
    }
    (PUBLIC / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    (PUBLIC / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"build {version}: {len(qs)} questões, {len(index) // CHUNK + 1} blocos, {len(theory)} cards de teoria")


if __name__ == "__main__":
    main()
