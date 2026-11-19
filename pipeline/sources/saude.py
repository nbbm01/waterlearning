"""Provas de saúde: Revalida e ENARE (residência médica e multiprofissional) do HealthQA-BR (Larxel/healthqa-br,
CC-BY-4.0, financiado pelo Ministério da Saúde) e o USMLE, exame de licença médica dos EUA, do MedQA traduzido
(cabralski/MedQA-ptBR). Baixe antes com hf_fetch.py.
"""
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, classify_topic, needs_figure, write_out

HEALTHQA = RAW / "hf" / "healthqa" / "healthqa-br.jsonl"
MEDQA = [(RAW / "hf" / "medqa" / f"{split}.jsonl", split) for split in ("train", "dev", "test")]

# especialidade do ENARE → (matéria, tópico); None = palavras-chave dentro da matéria
GROUPS = {
    "Cardiologia": ("med", "med-cardiologia"), "Medicina de Família, Preventiva e Saúde Coletiva": ("med", "med-preventiva"),
    "Cirurgia Geral": ("med", "med-cirurgia"), "Cirurgia Plástica": ("med", "med-cirurgia"), "Cirurgia Torácica": ("med", "med-cirurgia"),
    "Cirurgia Vascular e Angiologia": ("med", "med-cirurgia"), "Cirurgia do Aparelho Digestivo": ("med", "med-cirurgia"),
    "Neurocirurgia": ("med", "med-cirurgia"), "Cirurgia de Cabeça e Pescoço": ("med", "med-cirurgia"), "Anestesiologia": ("med", "med-cirurgia"),
    "Ginecologia e Obstetrícia": ("med", "med-gineco-obstetricia"), "Radiologia e Diagnóstico por Imagem": ("med", "med-radiologia"),
    "Pediatria": ("med", "med-pediatria"), "Medicina do Adolescente": ("med", "med-pediatria"),
    "Hematologia e Hemoterapia": ("med", "med-hemato-onco"), "Oncologia": ("med", "med-hemato-onco"), "Neurologia": ("med", "med-neurologia"),
    "Patologia": ("med", "med-patologia-genetica"), "Nefrologia": ("med", "med-nefrologia"), "Psiquiatria": ("med", "med-psiquiatria"),
    "Ortopedia e Traumatologia": ("med", "med-ortopedia"), "Medicina Física e Reabilitação": ("med", "med-ortopedia"),
    "Oftalmologia": ("med", "med-oftalmo-otorrino"), "Otorrinolaringologia": ("med", "med-oftalmo-otorrino"), "Foniatria": ("med", "med-oftalmo-otorrino"),
    "Infectologia": ("med", "med-infectologia"), "Endoscopia Digestiva": ("med", "med-gastro"), "Gastroenterologia": ("med", "med-gastro"),
    "Endocrinologia e Metabologia": ("med", "med-endocrinologia"), "Pneumologia": ("med", "med-pneumologia"),
    "Medicina Intensiva": ("med", "med-emergencia"), "Medicina de Emergência": ("med", "med-emergencia"),
    "Alergia e Imunologia": ("med", "med-reumatologia"), "Reumatologia": ("med", "med-reumatologia"), "Dermatologia": ("med", "med-dermatologia"),
    "Clínica Médica": ("med", None), "Homeopatia": ("med", None),
    "Saúde coletiva": ("sau", "sau-saude-coletiva"), "Ciências biológicas": ("sau", "sau-outras"), "Biomedicina": ("sau", "sau-farmacia"),
    "Farmácia": ("sau", "sau-farmacia"), "Odontologia": ("sau", "sau-odontologia"), "Fonoaudiologia": ("sau", "sau-fonoaudiologia"),
    "Terapia ocupacional": ("sau", "sau-fisioterapia"), "Fisioterapia": ("sau", "sau-fisioterapia"), "Serviço social": ("sau", "sau-servico-social"),
    "Enfermagem": ("sau", "sau-enfermagem"), "Nutrição": ("sau", "sau-nutricao"), "Educação física": ("sau", "sau-outras"),
    "Física médica": ("sau", "sau-outras"), "Medicina veterinária": ("sau", "sau-outras"), "Psicologia": ("psi", None),
}
OPTION = re.compile(r"\n'([A-E])': '(.*?)'(?=\n'[A-E]': |\s*$)", re.S)


def clean(text):
    text = re.sub(r"[ \t ]+", " ", (text or "").replace("\r", ""))
    text = re.sub(r" *\n *", "\n", text)
    # o PDF quebra linha no meio da frase; mantém só quebras de parágrafo
    text = re.sub(r"(?<![.:;?!])\n(?!\n)(?=[a-zà-ú(])", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def last_sentence(text):
    """a pergunta de verdade fica no fim do caso clínico ("Qual é o próximo passo...?")"""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return parts[-1] if parts else ""


def healthqa(out, skipped):
    for line in open(HEALTHQA, encoding="utf-8"):
        r = json.loads(line)
        opts = OPTION.findall(r["question"])
        letters = [k for k, _ in opts]
        if letters != list("ABCDE"[: len(letters)]) or len(letters) < 4 or r["answer"] not in letters:
            skipped["alternativas"] += 1
            continue
        stem = clean(r["question"][: r["question"].find("\n'A': ")])
        texts = [clean(t) for _, t in opts]
        if needs_figure(stem) or not all(texts) or len(set(texts)) < len(texts):
            skipped["figura ou alternativas"] += 1
            continue
        source, group = r["source"], r.get("group")
        subj, topic = GROUPS.get(group, ("med", None)) if group else ("med", None)
        text = stem + " " + " ".join(texts)
        if not topic:
            focus = (group or "") + " " + last_sentence(stem) + " " + texts[letters.index(r["answer"])]
            topic = classify_topic(text, subj, focus)
        exam = "Revalida" if source == "Revalida" else "ENARE"
        kind = {"Enare Residência Médica": "residência médica", "Enare Multiprofissional": "residência multiprofissional"}.get(source)
        out.append({
            "id": f"hqa-{r['id']}", "s": subj, "e": exam, "y": int(r["year"]) if r.get("year") else None, "t": topic,
            "d": 3 if source == "Enare Residência Médica" else 2, "lvl": 3 if source == "Enare Residência Médica" else 2,
            "k": "text", "stem": stem, "opts": [{"t": t} for t in texts], "ans": letters.index(r["answer"]), "tags": [group] if group else [],
            "hint": group or "", "src": f"{exam} {r.get('year') or ''}".strip() + (f" ({kind})" if kind else "") + (f", {group}" if group else ""),
        })


def medqa(out, skipped):
    for path, split in MEDQA:
        for i, line in enumerate(open(path, encoding="utf-8")):
            r = json.loads(line)
            stem = clean(r["CONTEXT"])
            texts = [clean(r[f"OPTION_{k}"]) for k in "ABCD"]
            if r["ANSWER"] not in "ABCD" or not all(texts) or len(set(texts)) < 4 or len(stem) < 30:
                skipped["MedQA inválida"] += 1
                continue
            if needs_figure(stem):
                skipped["MedQA com figura"] += 1
                continue
            # o caso clínico cita muitos sistemas; a pergunta final e a resposta certa dizem o assunto
            focus = last_sentence(stem) + " " + texts["ABCD".index(r["ANSWER"])]
            out.append({
                "id": f"usmle-{split}-{i}", "s": "med", "e": "USMLE", "y": None,
                "t": classify_topic(stem + " " + " ".join(texts), "med", focus), "d": 3, "lvl": 3, "k": "text",
                "stem": stem, "opts": [{"t": t} for t in texts], "ans": "ABCD".index(r["ANSWER"]), "tags": [],
                "src": "USMLE (exame de licença médica dos EUA), via MedQA traduzido",
            })


def main():
    out, skipped = [], collections.Counter()
    healthqa(out, skipped)
    medqa(out, skipped)
    print("descartadas:", dict(skipped))
    print(collections.Counter((q["e"], q["s"]) for q in out).most_common())
    print(collections.Counter(q["t"] for q in out).most_common())
    write_out("saude", out)


if __name__ == "__main__":
    main()
