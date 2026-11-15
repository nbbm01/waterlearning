"""Junta pipeline/out/*.json + curadoria e gera public/data (index, chunks, meta, teoria)."""
import collections
import hashlib
import re
import json
import shutil
from pathlib import Path

from common import MILITARY, OUT, PIPE, PUBLIC, RATING, TAXONOMY, norm, subtopic

CHUNK = 60
F_COMMENTED, F_CLASSIC, F_MILITARY, F_IMAGE, F_DEEP = 1, 2, 4, 8, 16
# deslocamento de Elo por banca: provas mais seletivas valem mais
EXAM_OFFSET = {"ITA": 300, "IME": 300, "EN": 150, "AFA": 100, "EFOMM": 100, "EsPCEx": 100, "FUVEST": 100, "UNICAMP": 100,
               # prova de prefeitura é a aplicação mais direta que existe: entra primeiro no degrau
               "Prefeituras": -100}


# TQM Fundamental: amostra de 24 recortes teve 9 defeituosos (texto cortado, questões grudadas); fora até refazer o recorte
SKIP_SOURCES = {"tqmf", "tqmm"}


def load():
    questions = {}
    for f in sorted(OUT.glob("*.json")):
        if f.stem in SKIP_SOURCES:
            continue
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
    if not q.get("u"):  # a fonte não trouxe o subtópico (tópico da API, capítulo do livro, gerador)
        q["t"], q["u"] = subtopic(text_of(q), q["s"], q["t"], q.get("hint") or "")
    prerequisites(q)


def text_of(q):
    return q.get("raw") or (q.get("stem") or "") + " " + " ".join(o.get("t", "") for o in q.get("opts", []))


# Pré-requisitos, na ordem do livro: quem está em "Equação do 1º grau" ainda não estudou inequação,
# equação do 2º grau, módulo... Uma questão que exige um assunto posterior vai para esse assunto.
# (de onde sai, o que exige, para onde vai); a última regra que casar vence, então vão da mais básica à mais avançada.
INEQ = r"inequac|[<>≤≥⩽⩾≦≧]|\\(le|ge|lt|gt|leq|geq|leqslant|geqslant)\b"
# "x²" sim, "m²" (unidade) não
QUAD = r"segundo grau|2\s*[oº°] grau|bhaskara|discriminante|\b[xyzt]\s*(\^\s*\{?\s*2\b|²)|\b(maior|menor) raiz|\bduas raizes|\braizes (reais|distintas)"
# barra solta é ruído comum de OCR: só "|x ...|", \lvert, \left| ou a palavra
MODULE = r"\bmodulo\b|valor absoluto|\\lvert|\\left\s*\||\|\s*-?\d*\s*x\b[^|]{0,10}\|"
# base numérica com expoente variável (2^x) ou expoente que contém a incógnita (x^{2x-1})
EXP = r"exponencial|\b\d\s*\^\s*\{?\s*[xyz]\b|\^\s*\{[^}]*x[^}]*\}"
LOG = r"\blog\b|\blog_|\\log\b|logaritm"
# fatorial é Análise Combinatória; "f^-1", "f(g(x))", "inversa", "composta" são o capítulo de função composta/inversa
FACT = r"\)\s*!|\b\d\s*!(?![\w!])|\bfatorial"
INVCOMP = r"\^\s*\{?\s*-\s*1\s*\}?\s*\(|f\s*-1\s*\(|\b[fgh]\s*\(\s*[fgh]\s*\(|\b[fgh]\s*[o∘]\s*[fgh]\b|\\circ|funcao inversa|\binversa de|funcao composta"
EQ1, EQ2, IQ = "mat-equacao-1grau", "mat-equacao-2grau", "mat-inequacoes"
FUNCS = {"mat-funcoes-intro", "mat-funcao-afim", "mat-funcao-quadratica"}
GATES = [
    ({EQ1, EQ2, IQ}, FACT, "mat-arranjo-permutacao"),
    (FUNCS, INVCOMP, "mat-funcao-composta-inversa"),
    ({EQ1}, QUAD, EQ2),
    ({EQ1, EQ2}, INEQ, IQ),
    ({EQ1, EQ2, IQ}, MODULE, "mat-funcao-modular"),
    ({EQ1, EQ2, IQ}, EXP, "mat-exponencial"),
    ({EQ1, EQ2, IQ, "mat-exponencial"}, LOG, "mat-logaritmos"),
]
# discussão com parâmetro ("possível e indeterminada", "para que valores de m") é o fim do capítulo, não o meio
PARAM = r"possivel e (in)?determinad|\bimpossivel\b|\bindeterminad|parametro|quaisquer que sejam|para (que|quais) valores? d[eo] [a-z]\b|conjunto (verdade|solucao) unitario|\bm\s*≠|\bm\s*¹"
SUB_TOPIC = {sb["id"]: t["id"] for s in TAXONOMY["subjects"] for t in s["topics"] for sb in t.get("subs", [])}
moved = collections.Counter()


def prerequisites(q):
    if q["s"] != "mat" or not q.get("u"):
        return
    # a pista (título do capítulo) também conta: "Inequações do primeiro grau" não é equação do 1º grau
    text = norm(f"{q.get('hint') or ''} {text_of(q)}")
    for origin, pattern, dest in GATES:
        if q["u"] in origin and re.search(pattern, text):
            moved[(q["u"], dest)] += 1
            q["t"], q["u"] = SUB_TOPIC[dest], dest
    if q["u"] in (EQ1, EQ2, IQ) and re.search(PARAM, text):
        q["param"] = True


TOUGH = {"ITA", "IME"}
MILITARY_MID = {"EsPCEx", "EFOMM", "AFA", "EN", "EPCAr", "CN", "CMRJ", "EEAR"}
SELECTIVE = {"FUVEST", "UNICAMP"}
CONCURSOS = {"Concursos", "Banco do Brasil", "Caixa", "Prefeituras"}


def calibrate(q):
    """dificuldade numa escala única, na lógica de um livro didático:
    1 = treino (conta direta), 2 = aplicação (problema, vestibular regional), 3 = vestibular exigente.
    A fonte só desempata dentro do nível da banca."""
    e, d = q["e"], q["d"]
    if q["id"].startswith("tae-"):  # Tópicos de Álgebra Elementar é preparatório militar do 1º ao último exercício
        q["deep"] = True
        return 3
    if q.get("param"):
        return 3
    if e == "Waterlearning":  # o gerador já sabe se é treino ou problema
        return d
    if e in TOUGH:
        return 3
    if e in MILITARY_MID or e in SELECTIVE:
        return 3 if d >= 2 else 2
    if e in CONCURSOS:  # problema contextualizado; o nível 1 é só fixação (conta direta, das questões autorais)
        return 2
    if e == "ENEM":  # contextualizado por natureza: no mínimo aplicação
        return max(2, d)
    return max(2, d)  # questões de vestibular (inclusive as dos livros) nunca são "treino"


# as próprias regras entram na versão: mudar só a classificação também invalida o índice guardado na aba
RULES = Path(__file__).read_text(encoding="utf-8") + (PIPE / "levels.json").read_text(encoding="utf-8")
LEVELS = {k: v for k, v in json.loads((PIPE / "levels.json").read_text(encoding="utf-8")).items() if k != "_"}


def audited(q):
    """correções feitas olhando a questão (pipeline/levels.json) vencem as regras automáticas"""
    fix = LEVELS.get(q["id"])
    if fix:
        if "u" in fix:
            q["t"], q["u"] = SUB_TOPIC[fix["u"]], fix["u"]
        q["d"] = fix.get("d", q["d"])
        q["drop"] = fix.get("drop", False)
        q["deep"] = fix.get("deep", q.get("deep"))


def main():
    qs = load()
    quarantine = PIPE / "quarantine.json"
    if quarantine.exists():  # fórmulas quebradas apontadas por audit_render.ts
        blocked = set(json.loads(quarantine.read_text(encoding="utf-8")))
        qs = [q for q in qs if q["id"] not in blocked]
    for q in qs:
        classify(q)
        q["d"] = calibrate(q)
        audited(q)
    qs = [q for q in qs if not q.get("drop")]
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
    version = hashlib.sha1((json.dumps(qs, ensure_ascii=False, sort_keys=True) + RULES).encode()).hexdigest()[:10]
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
            # aprofundamento: ITA/IME e material de olimpíada ficam fora do treino normal;
            # o difícil de FUVEST, UNICAMP e militares é vestibular comum e fica no Difícil
            if q["e"] in TOUGH or q.get("deep"):
                flags |= F_DEEP
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
    for (src, dest), n in sorted(moved.items()):
        print(f"pré-requisito: {n} de {src} → {dest}")
    print(f"build {version}: {len(qs)} questões, {len(index) // CHUNK + 1} blocos, {len(theory)} cards de teoria")


if __name__ == "__main__":
    main()
