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


# ---------------------------------------------------------------- química, por outro caminho
# outra tabela e outro parser (pilha de multiplicadores lida de trás para frente), para não herdar um erro do gerador
MASS = {"H": 1.0, "C": 12.0, "N": 14.0, "O": 16.0, "Na": 23.0, "Mg": 24.0, "Al": 27.0, "S": 32.0, "Cl": 35.5, "K": 39.0, "Ca": 40.0,
        "Fe": 56.0, "Zn": 65.0}


def composition(formula):
    counts, mult, num = {}, [1], ""
    for ch in reversed(formula):
        if ch.isdigit():
            num = ch + num
        elif ch == ")":
            mult.append(mult[-1] * int(num or 1))
            num = ""
        elif ch == "(":
            mult.pop()
        elif ch.islower():
            num = ch + "|" + num  # segunda letra do símbolo: junta com a maiúscula seguinte (na leitura reversa)
        else:
            low, _, digits = num.partition("|") if "|" in num else ("", "", num)
            el = ch + low
            counts[el] = counts.get(el, 0) + int(digits or 1) * mult[-1]
            num = ""
    return counts


def mass(formula):
    return sum(MASS[el] * n for el, n in composition(formula).items())


def smallest_coefficients(left, right):
    """força bruta: menores inteiros (até 8) que conservam todos os átomos"""
    import itertools
    species = left + right
    for total in range(len(species), 8 * len(species) + 1):
        for cs in itertools.product(range(1, 9), repeat=len(species)):
            if sum(cs) != total:
                continue
            bal = {}
            for i, (c, f) in enumerate(zip(cs, species)):
                for el, n in composition(f).items():
                    bal[el] = bal.get(el, 0) + (c * n if i < len(left) else -c * n)
            if not any(bal.values()):
                return dict(zip(species, cs))
    raise ValueError(f"sem balanceamento: {left} -> {right}")


def number(text):
    """valor da alternativa: '1,5 mol', '2.904 g', '\\(6\\cdot10^{23}\\)' ou '13'"""
    m = re.search(r"\\\(([\d,]+)\\cdot10\^\{(-?\d+)\}\\\)", text)
    if m:
        return float(m.group(1).replace(",", ".")) * 10 ** int(m.group(2))
    m = re.search(r"-?\d{1,3}(?:\.\d{3})+(?:,\d+)?|-?\d+(?:,\d+)?", text)
    return float(m.group().replace(".", "").replace(",", "."))


def chem_truth(c):
    k = c["kind"]
    if k == "massa_molar":
        return mass(c["f"])
    if k == "mol":
        return float(Fraction(c["m"])) / mass(c["f"])
    if k == "massa":
        return float(Fraction(c["n"])) * mass(c["f"])
    if k == "moleculas":
        return float(Fraction(c["m"])) / mass(c["f"]) * 6e23
    if k == "atomos":
        return float(Fraction(c["m"])) / mass(c["f"]) * composition(c["f"])[c["el"]] * 6e23
    if k in ("soma_coef", "coef"):
        coefs = smallest_coefficients(c["left"], c["right"])
        return sum(coefs.values()) if k == "soma_coef" else coefs[c["f"]]
    if k in ("mol_mol", "massa_massa"):
        coefs = smallest_coefficients([f for _, f in c["left"]], [f for _, f in c["right"]])
        ratio = coefs[c["b"]] / coefs[c["a"]]
        if k == "mol_mol":
            return float(Fraction(c["na"])) * ratio
        return float(Fraction(c["ma"])) / mass(c["a"]) * ratio * mass(c["b"])
    if k == "cntp":
        return float(Fraction(c["m"])) / mass(c["f"]) * 22.4
    if k == "clapeyron":
        return float(Fraction(c["n"])) * 0.082 * (c["tc"] + 273) / c["P"]
    if k == "conc_comum":
        return float(Fraction(c["m"])) / (c["V"] / 1000)
    if k == "molaridade":
        return float(Fraction(c["m"])) / mass(c["f"]) / (c["V"] / 1000)
    if k == "diluicao":
        return float(Fraction(c["C1"])) * c["V1"] / c["V2"]
    raise ValueError(k)


def close(a, b):
    return abs(a - b) <= 0.006 * max(abs(a), abs(b), 1e-9)


def audit_chemistry(qs):
    checked, bad = 0, []
    for q in qs:
        if "chk" not in q:
            continue
        truth = chem_truth(q["chk"])
        marked = number(q["opts"][q["ans"]]["t"])
        others = [number(o["t"]) for k, o in enumerate(q["opts"]) if k != q["ans"]]
        checked += 1
        if not close(marked, truth) or any(close(v, truth) for v in others):
            bad.append((q["id"], truth, marked, others))
    print(f"{checked} questões de química conferidas, {len(bad)} com problema")
    for b in bad[:10]:
        print("  ", b)
    return bad


def main():
    qs = json.loads(OUT.read_text(encoding="utf-8"))
    chem_bad = audit_chemistry(qs)
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
    if bad or chem_bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
