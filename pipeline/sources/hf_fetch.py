"""Baixa os bancos abertos do Hugging Face para pipeline/raw/hf/<nome>/ e converte parquet em JSONL.

Os importadores só leem JSON(L) com a biblioteca padrão; o pyarrow entra apenas aqui:
    uv run --with pyarrow python3 -I pipeline/sources/hf_fetch.py [nome ...]
Arquivo já baixado não é pedido de novo.
"""
import json
import sys
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "raw" / "hf"

# nome local → (repositório, arquivos). Licença e origem de cada um estão em SOURCES.md.
DATASETS = {
    "mmmlu": ("openai/MMMLU", ["test/mmlu_PT-BR.csv"]),
    "mmlupx": ("li-lab/MMLU-ProX", ["pt/test-00000-of-00001.parquet", "pt/validation-00000-of-00001.parquet"]),
    "medqa": ("cabralski/MedQA-ptBR", ["train.parquet", "dev.parquet", "test.parquet"]),
    "healthqa": ("Larxel/healthqa-br", ["healthqa-br.parquet"]),
    "oab": ("russ7/oab_exams_2011_2025_combined", ["data/train-00000-of-00001.parquet"]),
    "vestibular": ("CEIA-POSITIVO/vestibular-gen_qa", ["data/train-00000-of-00001.parquet"]),
    "ptexams": ("amalia-llm/pt_exams", ["all.json"]),
    "enade": ("northern-64bit/ENADE_Brazilian_national_university_examination_MCQ_483",
              ["ENADE_Brazilian_national_university_examination_MCQ.json"]),
    "poscomp": ("maritaca-ai/poscomp", ["data/train-00000-of-00001.parquet"]),
    "enem24": ("maritaca-ai/enem", ["2024.jsonl"]),
}
# colunas que não interessam e pesam (raciocínios gerados por modelo)
DROP = {"vestibular": {"qa_pairs", "usage"}}


def download(repo, path, dest):
    if dest.exists() and dest.stat().st_size:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://huggingface.co/datasets/{repo}/resolve/main/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "waterlearning-pipeline/0.1"})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest.with_suffix(".part"), "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    dest.with_suffix(".part").rename(dest)


def to_jsonl(parquet, out, drop):
    import pyarrow.parquet as pq

    table = pq.read_table(parquet, columns=[c for c in pq.read_schema(parquet).names if c not in drop])
    with open(out, "w", encoding="utf-8") as f:
        for row in table.to_pylist():
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return table.num_rows


def main(names):
    for name in names or DATASETS:
        repo, files = DATASETS[name]
        folder = RAW / name
        for path in files:
            dest = folder / Path(path).name
            download(repo, path, dest)
            if dest.suffix == ".parquet":
                out = dest.with_suffix(".jsonl")
                if not out.exists():
                    n = to_jsonl(dest, out, DROP.get(name, set()))
                    print(f"{name}: {dest.name} → {n} linhas")
        print(f"{name}: ok ({repo})", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
