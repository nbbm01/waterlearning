"""Baixa questões da API das Questões (apidasquestoes.com.br) com cache em disco e controle de cota.

Cada questão entregue e cada gabarito consultado consomem cota; nada é pedido duas vezes.
Uso: python3 qdq_fetch.py counts | fetch [orçamento]
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, ROOT

API = "https://api.apidasquestoes.com.br/api/v1"
CACHE = RAW / "qdq"
RESERVE = 50  # nunca gasta a cota até o fim
SUBJECTS = {10: "mat", 103: "fis", 109: "his"}
# instituição/banca → rótulo no banco; ordem = prioridade
TARGETS = [
    ("instituicaoId", 1795, "EsPCEx"),
    ("bancaId", "Marinha", "Marinha"), ("bancaId", "DIRENS Aeronáutica", "Aeronáutica"), ("bancaId", "IME", "IME"),
    ("bancaId", "DECEx", "Exército"), ("bancaId", "CMRJ", "CMRJ"), ("bancaId", "FUVEST", "FUVEST"),
    ("bancaId", "COMVEST UNICAMP", "UNICAMP"), ("bancaId", "DSEA UERJ", "UERJ"), ("bancaId", "COPERSE UFRGS", "UFRGS"),
    ("bancaId", "COPEVE UFMG", "UFMG"), ("bancaId", "NC UFPR (FUNPAR)", "UFPR"),
]
state = {"left": None}


def key():
    k = os.environ.get("QDQ_API_KEY")
    if not k:
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith("QDQ_API_KEY="):
                k = line.split("=", 1)[1].strip()
    return k


def get(path, params=None, auth=True):
    url = f"{API}{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
    cached = CACHE / "http" / (urllib.parse.quote(path + "?" + urllib.parse.urlencode(sorted((params or {}).items())), safe="") + ".json")
    if cached.exists():
        return json.loads(cached.read_text())
    if auth and state["left"] is not None and state["left"] <= RESERVE:
        raise SystemExit(f"cota quase no fim ({state['left']} restantes); parando")
    headers = {"User-Agent": "waterlearning-pipeline/0.1", "Accept": "application/json"}
    if auth:
        headers["X-Api-Key"] = key()
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                left = r.headers.get("x-quota-questoes-restantes")
                if left is not None:
                    state["left"] = int(left)
                data = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(20 * (attempt + 1))
                continue
            raise SystemExit(f"{e.code} em {path}: {e.read()[:300]!r}")
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(data, ensure_ascii=False))
    time.sleep(1.1)  # limite de requisições por minuto
    return data


def resolve_bancas():
    bancas = {b["label"]: b["id"] for b in get("/bancas", auth=False)}
    return [(field, bancas[ident] if isinstance(ident, str) else ident, label)
            for field, ident, label in TARGETS if not isinstance(ident, str) or ident in bancas]


def counts():
    total = {}
    for field, ident, label in resolve_bancas():
        for mid, subj in SUBJECTS.items():
            page = get("/questoes", {field: ident, "materiaId": mid, "page": 0, "size": 1})
            total[(label, subj)] = total.get((label, subj), 0) + page["totalElements"]
    for (label, subj), n in total.items():
        print(f"{label:8s} {subj} {n}")
    print("cota restante:", state["left"])


def fetch(budget, only=None):
    """baixa páginas de 50 e os gabaritos, por prioridade, até gastar `budget` de cota"""
    start = state["left"]
    spent = lambda: (start - state["left"]) if start is not None and state["left"] is not None else 0
    for field, ident, label in resolve_bancas():
        if only and label != only:
            continue
        for mid, subj in SUBJECTS.items():
            page_no = 0
            while True:
                page = get("/questoes", {field: ident, "materiaId": mid, "page": page_no, "size": 50})
                if start is None:
                    start = state["left"]
                for q in page["content"]:
                    if q.get("certoOuErrado") or q.get("anulada") or q.get("desatualizada") or len(q.get("options") or []) < 4:
                        continue
                    out = CACHE / "questions" / f"{q['id']}.json"
                    if out.exists():
                        continue
                    gab = get(f"/questoes/{q['id']}/gabarito")
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(json.dumps({"q": q, "gab": gab, "label": label, "subject": subj}, ensure_ascii=False))
                    if spent() >= budget:
                        print(f"orçamento de {budget} atingido; cota restante {state['left']}")
                        return
                if page.get("last", True):
                    break
                page_no += 1
            print(f"{label} {subj}: ok (gasto até agora {spent()}, restante {state['left']})")


# assuntos básicos que os vestibulares cobram dentro de problemas e quase nunca rotulam:
# (topicoId da API, máximo de questões)
BASICS = [
    (11940, 160), (11952, 110), (11941, 110), (11954, 90), (11953, 70), (11931, 90), (11932, 60),
    (11929, 70), (11934, 110), (11916, 70), (11920, 50), (11945, 50), (11926, 50), (11955, 40),
]


def fetch_topics(budget):
    """múltipla escolha de nível médio/superior nos tópicos BASICS, até gastar `budget` de cota"""
    start = None
    for topic_id, limit in BASICS:
        taken, page_no = 0, 0
        while taken < limit:
            params = {"materiaId": 10, "topicoId": topic_id, "certoOuErrado": "false", "anulada": "false",
                      "nivel": "MEDIO,SUPERIOR", "page": page_no, "size": 50}
            page = get("/questoes", params)
            if start is None:
                start = state["left"]
            for q in page["content"]:
                if taken >= limit:
                    break
                if q.get("certoOuErrado") or q.get("anulada") or q.get("desatualizada") or len(q.get("options") or []) < 4:
                    continue
                out = CACHE / "questions" / f"{q['id']}.json"
                if not out.exists():
                    gab = get(f"/questoes/{q['id']}/gabarito")
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(json.dumps({"q": q, "gab": gab, "label": "Concursos", "subject": "mat"}, ensure_ascii=False))
                taken += 1
                if start is not None and state["left"] is not None and start - state["left"] >= budget:
                    print(f"orçamento de {budget} atingido; cota restante {state['left']}")
                    return
            if page.get("last", True):
                break
            page_no += 1
        print(f"tópico {topic_id}: {taken} questões (cota restante {state['left']})")


if __name__ == "__main__":
    if sys.argv[1] == "counts":
        counts()
    elif sys.argv[1] == "topics":
        fetch_topics(int(sys.argv[2]) if len(sys.argv) > 2 else 2300)
    else:
        fetch(int(sys.argv[2]) if len(sys.argv) > 2 else 4500, sys.argv[3] if len(sys.argv) > 3 else None)
