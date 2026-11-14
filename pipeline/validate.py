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
    for row in index:
        qid, s, e, y, t, d, flags, cid, rating = row
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
        totals[(meta["subjects"][s]["name"], meta["exams"][e])] += 1
        kinds[q["k"]] += 1

    print(f"Total: {len(index)} questões  ({kinds['text']} em texto, {kinds['image']} em recorte)")
    by_subject = collections.Counter()
    for (s, e), n in sorted(totals.items()):
        by_subject[s] += n
        print(f"  {s:11s} {e:10s} {n}")
    print("  " + "  ".join(f"{s}: {n}" for s, n in by_subject.items()))
    if errors:
        print(f"\n{len(errors)} problema(s):")
        for e in errors[:40]:
            print("  -", e)
        sys.exit(1)
    print("Sem problemas.")


if __name__ == "__main__":
    main()
