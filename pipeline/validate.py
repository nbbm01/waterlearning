"""Confere o banco gerado em public/data e imprime os totais."""
import collections
import json
import re
import sys

from common import PUBLIC, ROOT

IMG = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")


def main():
    meta = json.loads((PUBLIC / "meta.json").read_text(encoding="utf-8"))
    index = json.loads((PUBLIC / "index.json").read_text(encoding="utf-8"))
    chunks = {}
    errors, ids = [], set()
    totals = collections.Counter()
    kinds = collections.Counter()
    tracks = collections.Counter()
    group_of = {e: g["name"] for g in meta["groups"] for e in g["exams"]}
    for row in index:
        qid, s, e, y, t, d, flags, cid, rating, u, mask = row
        if not mask:
            errors.append(f"{qid}: fora de todas as trilhas ({meta['exams'][e]}, {meta['subjects'][s]['name']})")
        for i, tr in enumerate(meta["tracks"]):
            if mask & (1 << i):
                tracks[tr["name"]] += 1
        if qid in ids:
            errors.append(f"{qid}: id duplicado")
        ids.add(qid)
        if cid not in chunks:
            chunks[cid] = json.loads((PUBLIC / "chunks" / f"{cid}.json").read_text(encoding="utf-8"))
        q = chunks[cid].get(qid)
        if not q:
            errors.append(f"{qid}: ausente do bloco {cid}")
            continue
        n = len(q["opts"]) if q["k"] == "text" else q.get("n", 0)
        if not 2 <= n <= 5:
            errors.append(f"{qid}: {n} alternativas")
        if not isinstance(q.get("ans"), int) or not 0 <= q["ans"] < n:
            errors.append(f"{qid}: gabarito inválido ({q.get('ans')})")
        if d not in (1, 2, 3):
            errors.append(f"{qid}: dificuldade {d}")
        paths = list(q.get("imgs") or [])
        if q["k"] == "text":
            if not (q.get("stem") or "").strip():
                errors.append(f"{qid}: enunciado vazio")
            paths += IMG.findall(q.get("stem") or "")
            for o in q["opts"]:
                if o.get("img"):
                    paths.append(o["img"])
                elif not (o.get("t") or "").strip():
                    errors.append(f"{qid}: alternativa vazia")
        elif not paths:
            errors.append(f"{qid}: questão em imagem sem recorte")
        for p in paths:
            if not (ROOT / "public" / p).exists():
                errors.append(f"{qid}: imagem ausente {p}")
        totals[(meta["subjects"][s]["name"], group_of.get(e, "?"))] += 1
        kinds[q["k"]] += 1

    print(f"Total: {len(index)} questões  ({kinds['text']} em texto, {kinds['image']} em recorte), {len(meta['exams'])} provas")
    by_subject, by_group = collections.Counter(), collections.Counter()
    for (s, g), n in totals.items():
        by_subject[s] += n
        by_group[g] += n
    for title, counter in (("Matérias", by_subject), ("Grupos de provas", by_group), ("Trilhas", tracks)):
        print(f"  {title}: " + ", ".join(f"{k} {n}" for k, n in counter.most_common()))
    if errors:
        print(f"\n{len(errors)} problema(s):")
        for e in errors[:40]:
            print("  -", e)
        sys.exit(1)
    print("Sem problemas.")


if __name__ == "__main__":
    main()
