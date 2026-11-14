"""ITA 2008–2026: provas objetivas oficiais (vestibular.ita.br), via o acervo versionado no repositório ita-api."""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from books import difficulty
from common import RAW, best_topic, norm, write_out
from exam_pdf import crop_questions, option_count, segment

DIR = RAW / "ita-api" / "data" / "vestibular" / "provas"
SUBJECTS = {"fisica": "fis", "matematica": "mat"}
START = re.compile(r"^Quest[ãa]o\s+(\d{1,2})\s*[.:]")
SECTION = re.compile(r"^(F[ÍI]SICA|MATEM[ÁA]TICA|QU[ÍI]MICA|PORTUGU[ÊE]S|INGL[ÊE]S|REDA[ÇC][ÃA]O)\s*$")
PAIR = re.compile(r"(\d{1,2})\s+([A-E]|\(?\*+\)?)(?=\s|$)")


def answer_key(pdf):
    """{matéria: {número: índice da alternativa}}; anuladas ficam de fora"""
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    lines = text.splitlines()
    head_i = next(i for i, l in enumerate(lines) if re.search(r"F[íi]sica", l) and re.search(r"Matem", l))
    heads = [(m.start(), norm(m.group(0))) for m in re.finditer(r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+", lines[head_i])]
    keys = {}
    for line in lines[head_i + 1:]:
        if re.search(r"Obs|anulad|considerad", line):
            break
        if not PAIR.search(line):
            continue
        for m in PAIR.finditer(line):
            col = min(heads, key=lambda h: abs(h[0] - m.start()))[1]
            if m.group(2) in "ABCDE":
                keys.setdefault(col, {})[int(m.group(1))] = "ABCDE".index(m.group(2))
    return keys


def topic(text, subject):
    t, _ = best_topic(text, subject, {"fis": "fis-dinamica", "mat": "mat-conjuntos-funcoes"}[subject])
    return t


def build(year, pdf, subject, answers, out):
    if not pdf.exists():
        return
    qs = {n: q for n, q in segment(pdf, START, SECTION).items() if n in answers}
    if not qs:
        print(f"  {pdf.name}: nenhuma questão com texto (provavelmente digitalizada)")
        return
    tag = f"ita{year}{subject}"
    imgs = crop_questions(pdf, qs, tag, "ita")
    nums = sorted(qs)
    for pos, num in enumerate(nums):
        q = qs[num]
        out.append({
            "id": f"ita-{year}-{subject}-{num}", "s": subject, "e": "ITA", "y": year, "t": topic(q["text"], subject),
            "d": difficulty(pos, len(nums), "ITA"), "k": "image", "opts": [], "n": max(option_count(q["text"]), answers[num] + 1),
            "ans": answers[num], "imgs": imgs[num], "tags": [], "raw": q["text"], "src": f"ITA {year}, {'Física' if subject == 'fis' else 'Matemática'}, questão {num}",
        })


def main():
    out = []
    for year in range(2008, 2027):
        key_pdf = DIR / f"prova_ita_vestibular_{year}_answer_key{'_1f' if year >= 2019 else ''}.pdf"
        if not key_pdf.exists():
            continue
        keys = answer_key(key_pdf)
        before = len(out)
        for col, subject in SUBJECTS.items():
            answers = keys.get(col, {})
            pdf = DIR / (f"prova_ita_vestibular_{year}_{col}.pdf" if year <= 2018 else f"prova_ita_vestibular_{year}_prova_1f.pdf")
            build(year, pdf, subject, answers, out)
        print(f"ITA {year}: {len(out) - before} questões")
    write_out("ita", out)


if __name__ == "__main__":
    main()
