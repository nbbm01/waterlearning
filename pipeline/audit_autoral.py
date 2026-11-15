"""Confere, por um caminho independente do gerador, o gabarito das questões autorais de equação do 1º grau.

O gerador escolhe x e monta a equação; aqui fazemos o contrário: lemos a equação do enunciado,
resolvemos (a expressão é linear, então f(0) e f(1) bastam) e comparamos com a alternativa marcada.
"""
import json
import re
from fractions import Fraction
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out" / "autoral.json"


def to_python(tex):
    s = tex
    s = re.sub(r"\\dfrac\{([^{}]+)\}\{([^{}]+)\}", r"((\1)/(\2))", s)
    s = s.replace("\\cdot", "*")
    s = re.sub(r"(\d)\s*x", r"\1*x", s)
    s = re.sub(r"(\d)\s*\(", r"\1*(", s)
    s = re.sub(r"(\d+)", r"Fraction(\1)", s)
    return s


def solve(eq):
    lhs, rhs = eq.split("=")
    f = lambda x: eval(to_python(lhs), {"Fraction": Fraction, "x": x}) - eval(to_python(rhs), {"Fraction": Fraction, "x": x})
    f0, f1 = f(Fraction(0)), f(Fraction(1))
    return -f0 / (f1 - f0)


def value(opt):
    m = re.fullmatch(r"\\\(x = (-?)(?:\\dfrac\{(\d+)\}\{(\d+)\}|(\d+))\\\)", opt)
    if not m:
        raise ValueError(f"alternativa fora do formato: {opt!r}")
    sign = -1 if m.group(1) else 1
    return sign * (Fraction(int(m.group(2)), int(m.group(3))) if m.group(2) else Fraction(int(m.group(4))))


def main():
    qs = json.loads(OUT.read_text(encoding="utf-8"))
    checked, bad = 0, []
    for q in qs:
        gen = q["id"].split("-")[1]
        if gen not in ("eq1_simples", "eq1_dois_lados", "eq1_fracao", "eq1_parenteses", "eq1_consecutivos", "eq1_mmc"):
            continue
        eq = re.search(r"\\\((.+?)\\\)", q["stem"]).group(1)
        truth = solve(eq)
        marked = value(q["opts"][q["ans"]]["t"])
        others = [value(o["t"]) for k, o in enumerate(q["opts"]) if k != q["ans"]]
        checked += 1
        if marked != truth or truth in others:
            bad.append((q["id"], eq, truth, marked))
    print(f"{checked} equações conferidas, {len(bad)} com problema")
    for b in bad[:10]:
        print("  ", b)


if __name__ == "__main__":
    main()
