"""Questões autorais geradas por computador para os assuntos básicos, com resolução passo a passo.

Princípios (psicologia do ensino):
- exemplo resolvido: toda questão traz a resolução, porque quem está começando aprende mais vendo o passo a passo;
- erros típicos viram alternativas: cada distrator é um engano comum, e a resolução diz qual é;
- números "limpos": a dificuldade fica no raciocínio, não em contas feias;
- a resposta é sempre calculada pelo programa, então o gabarito nunca está errado.
"""
import math
import random
import re
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import write_out

SRC = "Questão autoral Waterlearning (gerada e conferida por computador)"


def fmt(x, unit=""):
    """número no padrão brasileiro: vírgula decimal, ponto de milhar, sem zeros sobrando"""
    if isinstance(x, Fraction):
        if x.denominator == 1:
            x = x.numerator
        else:
            # vale dentro e fora de fórmula: decimal exato quando existe, senão a/b
            d = x.denominator
            while d % 2 == 0:
                d //= 2
            while d % 5 == 0:
                d //= 5
            x = float(x) if d == 1 else f"{x.numerator}/{x.denominator}"
            if isinstance(x, str):
                return f"{x} {unit}".strip() if unit else x
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    if isinstance(x, int):
        s = f"{x:,}".replace(",", ".")
    else:
        s = f"{x:,.2f}".rstrip("0").rstrip(".").replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} {unit}".strip() if unit else s


def money(x):
    return "R$ " + f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class Why:
    """alternativa errada com o diagnóstico do erro que leva a ela: o aluno que marca é avisado do que aconteceu"""

    def __init__(self, value, reason):
        self.value, self.reason = value, reason


class Builder:
    def __init__(self, gen, subject, topic, sub, seed):
        self.gen, self.subject, self.topic, self.sub = gen, subject, topic, sub
        self.rng = random.Random(f"{gen}-{seed}")
        self.seed = seed

    def make(self, stem, correct, wrong, explanation, d, show=str):
        """monta 5 alternativas distintas a partir da correta e de erros típicos"""
        opts, seen, why = [], set(), {}
        for w in [correct, *wrong]:
            v = w.value if isinstance(w, Why) else w
            key = show(v)
            if key not in seen:
                seen.add(key)
                opts.append(v)
                if isinstance(w, Why):
                    why[key] = w.reason
        # completa com vizinhos plausíveis; em valores grandes, "1.000 e 1.001" entrega a resposta, então o passo cresce
        num = isinstance(correct, (int, float, Fraction))
        step = 10 ** max(0, len(str(int(abs(correct)))) - 2) if num and abs(correct) >= 100 else 1
        bump = step
        while len(opts) < 5:
            if not num:  # sem como inventar vizinhos: repete a correta e main() descarta a semente
                opts += [correct] * (5 - len(opts))
                break
            for v in (correct + bump, correct - bump):
                if show(v) not in seen and len(opts) < 5:
                    seen.add(show(v))
                    opts.append(v)
            bump += step
        opts = opts[:5]
        order = list(range(5))
        self.rng.shuffle(order)
        shown = [opts[i] for i in order]
        return {
            "id": f"autoral-{self.gen}-{self.seed}", "s": self.subject, "e": "Waterlearning", "y": 0, "t": self.topic,
            "u": self.sub, "d": d, "k": "text", "stem": stem, "opts": [{"t": show(v), **({"why": why[show(v)]} if show(v) in why else {})} for v in shown],
            "ans": order.index(0), "exp": explanation, "tags": ["autoral"], "src": SRC,
        }


# ---------------------------------------------------------------- matemática

def show_x(v):
    """alternativa no formato x = valor, com fração em LaTeX quando não for inteiro"""
    v = Fraction(v)
    if v.denominator == 1:
        return f"\\(x = {v.numerator}\\)"
    sign = "-" if v < 0 else ""
    return f"\\(x = {sign}\\dfrac{{{abs(v.numerator)}}}{{{v.denominator}}}\\)"


def eq1_simples(b):
    r = b.rng
    x = r.randint(-9, 15) or 4
    a = r.choice([2, 3, 4, 5, 6, 7, 8, 9])
    k = r.randint(1, 30)
    plus = r.random() < 0.6
    c = a * x + k if plus else a * x - k
    sign, op = ("+", "-") if plus else ("-", "+")
    moved = c - k if plus else c + k
    stem = f"Qual é a solução da equação \\({a}x {sign} {k} = {c}\\)?"
    exp = (f"Isole o termo com \\(x\\). O \\({k}\\) está {'somando' if plus else 'subtraindo'}, então passa para o outro lado "
           f"{'subtraindo' if plus else 'somando'}:\n\n\\[{a}x = {c} {op} {k} = {moved}\\]\n\n"
           f"Agora divida pelo coeficiente: \\(x = \\dfrac{{{moved}}}{{{a}}} = {x}\\).\n\n"
           f"**Confira:** \\({a}\\cdot({x}) {sign} {k} = {c}\\). ✔\n\n"
           f"*Erro comum:* passar o \\({k}\\) para o outro lado sem trocar a operação, ou esquecer de dividir por \\({a}\\).")
    wrong = [Fraction(c + k if plus else c - k, a), moved, Fraction(c, a), -x]
    return b.make(stem, x, wrong, exp, 1, show=show_x)


def eq1_dois_lados(b):
    r = b.rng
    x = r.randint(-6, 12) or 3
    a, c = r.sample(range(2, 10), 2)
    if a < c:
        a, c = c, a
    bb = r.randint(-15, 15)
    d = a * x + bb - c * x
    stem = f"Resolva a equação \\({a}x {'+' if bb >= 0 else '-'} {abs(bb)} = {c}x {'+' if d >= 0 else '-'} {abs(d)}\\)."
    exp = (f"Junte os termos com \\(x\\) de um lado e os números do outro, trocando o sinal de quem muda de lado:\n\n"
           f"\\[{a}x - {c}x = {d} {'-' if bb >= 0 else '+'} {abs(bb)}\\]\n\n\\[{a - c}x = {d - bb}\\]\n\n"
           f"\\[x = \\dfrac{{{d - bb}}}{{{a - c}}} = {x}\\]\n\n"
           f"*Erro comum:* trocar o sinal só de um dos termos que mudou de lado.")
    wrong = [Fraction(d + bb, a - c), Fraction(d - bb, a + c), -x, Fraction(d - bb, a)]
    return b.make(stem, Fraction(x), wrong, exp, 1, show=show_x)


def eq1_fracao(b):
    r = b.rng
    kind = r.choice(["num", "div"])
    if kind == "num":  # (x ± a)/k = c
        k, c, a = r.choice([2, 3, 4, 5]), r.randint(-6, 30), r.randint(1, 15)
        minus = r.random() < 0.6
        x = k * c + a if minus else k * c - a
        stem = f"Resolva a equação \\(\\dfrac{{x {'-' if minus else '+'} {a}}}{{{k}}} = {c}\\)."
        exp = (f"Multiplique os dois lados por \\({k}\\) para tirar o denominador:\n\n\\[x {'-' if minus else '+'} {a} = {k * c}\\]\n\n"
               f"Agora passe o \\({a}\\) para o outro lado {'somando' if minus else 'subtraindo'}: \\(x = {k * c} {'+' if minus else '-'} {a} = {x}\\).\n\n"
               f"*Erro comum:* dividir só o \\({a}\\) por \\({k}\\), como se fosse \\(x {'-' if minus else '+'} \\dfrac{{{a}}}{{{k}}}\\).")
        wrong = [c + a if minus else c - a, k * c - a if minus else k * c + a, Fraction(c + a, k) if minus else Fraction(c - a, k), x + k]
        return b.make(stem, x, wrong, exp, 1, show=show_x)
    k, a = r.choice([2, 3, 4, 5, 6]), r.randint(1, 12)
    x = k * r.randint(-4, 12)
    c = x // k + a
    stem = f"Resolva a equação \\(\\dfrac{{x}}{{{k}}} + {a} = {c}\\)."
    exp = (f"Primeiro isole a fração: \\(\\dfrac{{x}}{{{k}}} = {c} - {a} = {c - a}\\).\n\n"
           f"Depois multiplique por \\({k}\\): \\(x = {c - a}\\cdot{k} = {x}\\).\n\n*Erro comum:* multiplicar só o \\(x\\) por {k} e esquecer os outros termos.")
    return b.make(stem, x, [c - a, (c + a) * k, k * c - a, Fraction(c - a, k)], exp, 1,
                  show=show_x)


def eq1_parenteses(b):
    r = b.rng
    k, a = r.choice([2, 3, 4, 5, 6]), r.randint(1, 9)
    x = r.randint(-5, 15)
    minus = r.random() < 0.5
    c = k * (x - a) if minus else k * (x + a)
    stem = f"Resolva a equação \\({k}(x {'-' if minus else '+'} {a}) = {c}\\)."
    exp = (f"**Jeito 1 (distributiva):** \\({k}x {'-' if minus else '+'} {k * a} = {c}\\), então \\({k}x = {c + k * a if minus else c - k * a}\\) e \\(x = {x}\\).\n\n"
           f"**Jeito 2 (mais rápido):** divida os dois lados por \\({k}\\): \\(x {'-' if minus else '+'} {a} = {c // k}\\), logo \\(x = {x}\\).\n\n"
           f"*Erro comum:* multiplicar só o \\(x\\) por {k} e esquecer o \\({a}\\) dentro dos parênteses.")
    wrong = [Fraction(c + a, k) if minus else Fraction(c - a, k), c // k, (c + a) // k if minus else (c - a) // k, -x]
    return b.make(stem, x, wrong, exp, 1,
                  show=show_x)


def eq1_consecutivos(b):
    r = b.rng
    n = r.choice([3, 3, 4, 5])
    x = r.randint(10, 400)
    total = n * x + n * (n - 1) // 2
    terms = " + ".join(["x"] + [f"(x + {k})" for k in range(1, n)])
    stem = f"Resolva a equação de primeiro grau \\({terms} = {total}\\)."
    exp = (f"Junte os \\(x\\) e junte os números: \\({n}x + {n * (n - 1) // 2} = {total}\\).\n\n"
           f"\\[{n}x = {total} - {n * (n - 1) // 2} = {total - n * (n - 1) // 2} \\Rightarrow x = {x}\\]\n\n"
           f"Essa é a forma algébrica de \"{n} números consecutivos somam {total}\": eles são {', '.join(str(x + k) for k in range(n))}.")
    return b.make(stem, x, [Fraction(total, n), x + 1, x - 1, total - n * (n - 1) // 2], exp, 1,
                  show=show_x)


PROBLEMS_1 = [
    ("A soma de um número com o seu {k}-plo é {t}. Qual é esse número?", lambda n, k: n * (k + 1),
     "Chame o número de \\(x\\). O enunciado vira \\(x + {k}x = {t}\\), ou seja, \\({k1}x = {t}\\). Logo \\(x = \\dfrac{{{t}}}{{{k1}}} = {n}\\)."),
    ("Ana tem o {k}-plo da idade de seu sobrinho. Juntos, eles têm {t} anos. Qual é a idade do sobrinho?", lambda n, k: n * (k + 1),
     "Se o sobrinho tem \\(x\\) anos, Ana tem \\({k}x\\). Juntos: \\(x + {k}x = {t}\\), então \\({k1}x = {t}\\) e \\(x = {n}\\) anos."),
    ("Um prêmio de {money} foi dividido entre dois irmãos de modo que o mais velho recebeu {k} vezes o que recebeu o mais novo. Quanto recebeu o mais novo?", lambda n, k: n * (k + 1),
     "Se o mais novo recebeu \\(x\\), o mais velho recebeu \\({k}x\\). Então \\(x + {k}x = {t}\\), ou seja, \\({k1}x = {t}\\), e \\(x = {n}\\) reais."),
]
MULT = {2: "dobro", 3: "triplo", 4: "quádruplo", 5: "quíntuplo"}


def eq1_problema(b):
    r = b.rng
    tpl, total, how = r.choice(PROBLEMS_1)
    k = r.choice([2, 3, 4, 5])
    n = r.randint(4, 40) * (50 if "prêmio" in tpl else 1)
    t = total(n, k)
    stem = tpl.replace("{k}-plo", MULT[k]).format(k=k, t=t, money=money(t))
    exp = ("**Traduza o texto para a equação.** " + how.format(k=k, k1=k + 1, t=t, n=n) +
           f"\n\n*Erro comum:* dividir o total por {k} em vez de {k + 1}: as partes são \\(x\\) e \\({k}x\\), que somam \\({k + 1}x\\).")
    is_money = "prêmio" in tpl
    show = (lambda v: money(v)) if is_money else (lambda v: fmt(v))
    wrong = [t // k if t % k == 0 else t / k, t - n, n * k, t // 2]
    return b.make(stem, n, wrong, exp, 2, show=show)


def sistema_galinhas(b):
    r = b.rng
    g, c = r.randint(5, 40), r.randint(3, 30)
    heads, legs = g + c, 2 * g + 4 * c
    stem = (f"Num sítio há galinhas e coelhos, num total de {heads} cabeças e {legs} pés. "
            f"Quantos coelhos há no sítio?")
    exp = (f"Sejam \\(g\\) galinhas e \\(c\\) coelhos. Cabeças: \\(g + c = {heads}\\). Pés: \\(2g + 4c = {legs}\\).\n\n"
           f"Multiplique a primeira por 2 e subtraia da segunda: \\(2c = {legs} - {2 * heads} = {legs - 2 * heads}\\), logo \\(c = {c}\\).\n\n"
           f"**Confira:** {g} galinhas e {c} coelhos dão \\(2\\cdot{g} + 4\\cdot{c} = {legs}\\) pés. ✔")
    return b.make(stem, c, [g, legs // 4, heads - legs // 4, legs - 2 * heads], exp, 2, show=lambda v: f"{v} coelhos")


def poly2(a, b, c, var="x"):
    """ax² + bx + c como se escreve à mão: sem "1x", "+ 0x" nem "+ 0" """
    terms = []
    for coef, part in ((a, f"{var}^2"), (b, var), (c, "")):
        if coef == 0:
            continue
        mag = "" if abs(coef) == 1 and part else str(abs(coef))
        sign = ("-" if coef < 0 else "") if not terms else (" - " if coef < 0 else " + ")
        terms.append(f"{sign}{mag}{part}")
    return "".join(terms) or "0"


def eq2_raizes(b):
    r = b.rng
    # completa: as incompletas (b = 0) têm gerador próprio, que ensina o atalho certo
    x1, x2 = r.sample([v for v in range(-9, 10) if v], 2)
    while x1 + x2 == 0:
        x2 = r.choice([v for v in range(-9, 10) if v and v != x1])
    s, p = x1 + x2, x1 * x2
    stem = f"Quais são as raízes da equação \\({poly2(1, -s, p)} = 0\\)?"
    delta = s * s - 4 * p
    exp = (f"Use Bhaskara com \\(a = 1\\), \\(b = {-s}\\), \\(c = {p}\\).\n\n"
           f"\\[\\Delta = b^2 - 4ac = {(-s) ** 2} - 4\\cdot1\\cdot({p}) = {delta}\\]\n\n"
           f"\\[x = \\dfrac{{-b \\pm \\sqrt{{\\Delta}}}}{{2a}} = \\dfrac{{{s} \\pm {int(math.isqrt(delta))}}}{{2}}\\]\n\n"
           f"Então \\(x = {max(x1, x2)}\\) ou \\(x = {min(x1, x2)}\\).\n\n"
           f"**Atalho (soma e produto):** procure dois números que somam \\({s}\\) e multiplicam \\({p}\\).\n\n"
           f"**Confira:** \\(({x1})^2 {'+' if -s >= 0 else '-'} {abs(s)}\\cdot({x1}) {'+' if p >= 0 else '-'} {abs(p)} = 0\\). ✔")
    pair = lambda a, c: f"\\({min(a, c)}\\) e \\({max(a, c)}\\)"
    correct = (x1, x2)
    wrong = [Why((-x1, -x2), f"Os sinais ficaram trocados. As raízes **somam** \\(-\\dfrac{{b}}{{a}} = {s}\\), com o sinal oposto ao de \\(b\\). Confira substituindo: com os seus valores a conta não dá zero."),
             Why((x1, -x2), "Uma das raízes está certa e a outra está com o sinal errado. Substitua cada uma na equação: as duas precisam zerar."),
             Why((s, p), f"Esses são a **soma** ({s}) e o **produto** ({p}) das raízes, não as raízes. Procure dois números que somam {s} e multiplicam {p}."),
             Why((-x1, x2), "Uma das raízes está certa e a outra está com o sinal errado. Substitua cada uma na equação: as duas precisam zerar."),
             Why((x1 + 1, x2 - 1), "Escorregou na conta do \\(\\Delta\\) ou da raiz. Confira substituindo os valores: eles não zeram a equação.")]
    return b.make(stem, correct, wrong, exp, 2, show=lambda v: pair(*v))


def delta(b):
    r = b.rng
    a, bb, c = r.randint(1, 4), r.randint(-9, 9), r.randint(-9, 9)
    d = bb * bb - 4 * a * c
    stem = f"Qual é o valor do discriminante \\(\\Delta\\) da equação \\({poly2(a, bb, c)} = 0\\)?"
    exp = (f"\\(\\Delta = b^2 - 4ac\\), com \\(a = {a}\\), \\(b = {bb}\\) e \\(c = {c}\\):\n\n"
           f"\\[\\Delta = ({bb})^2 - 4\\cdot{a}\\cdot({c}) = {bb * bb} {'-' if 4 * a * c >= 0 else '+'} {abs(4 * a * c)} = {d}\\]\n\n"
           f"*Erro comum:* esquecer que \\(({bb})^2\\) é sempre positivo, ou errar o sinal de \\(-4ac\\) quando \\(c\\) é negativo.")
    return b.make(stem, d, [Why(-bb * bb - 4 * a * c, f"\\(b^2\\) é sempre positivo: \\(({bb})^2 = {bb * bb}\\), não \\({-bb * bb}\\)."),
                            Why(bb * bb + 4 * a * c, f"O sinal do \\(-4ac\\) ficou trocado: \\(-4\\cdot{a}\\cdot({c}) = {-4 * a * c}\\)."),
                            Why(bb - 4 * a * c, "Faltou elevar o \\(b\\) ao quadrado."),
                            Why(2 * bb - 4 * a * c, "\\(b^2\\) é \\(b \\cdot b\\), não \\(2b\\).")], exp, 1, show=fmt)


def afim_valor(b):
    r = b.rng
    a, c, k = r.choice([-5, -4, -3, -2, 2, 3, 4, 5, 6]), r.randint(-10, 10), r.randint(-5, 8)
    y = a * k + c
    stem = f"Dada a função \\(f(x) = {a}x {'+' if c >= 0 else '-'} {abs(c)}\\), qual é o valor de \\(f({k})\\)?"
    exp = (f"Substitua \\(x\\) por \\({k}\\):\n\n\\[f({k}) = {a}\\cdot({k}) {'+' if c >= 0 else '-'} {abs(c)} = {a * k} {'+' if c >= 0 else '-'} {abs(c)} = {y}\\]\n\n"
           "*Erro comum:* esquecer os parênteses quando o número substituído é negativo.")
    return b.make(stem, y, [a + k + c, a * k - c, -y, a * (k + c)], exp, 1, show=fmt)


def afim_raiz(b):
    r = b.rng
    root = r.randint(-8, 10) or 2
    a = r.choice([-4, -3, -2, 2, 3, 4, 5])
    c = -a * root
    stem = f"Qual é a raiz (o zero) da função \\(f(x) = {a}x {'+' if c >= 0 else '-'} {abs(c)}\\)?"
    exp = (f"A raiz é o valor de \\(x\\) que torna \\(f(x) = 0\\):\n\n\\[{a}x {'+' if c >= 0 else '-'} {abs(c)} = 0 \\Rightarrow {a}x = {-c} \\Rightarrow x = {root}\\]\n\n"
           f"No gráfico, é onde a reta corta o eixo \\(x\\).\n\n*Erro comum:* responder o coeficiente linear (\\({c}\\)), que é onde a reta corta o eixo \\(y\\).")
    return b.make(stem, root, [-root, c, Fraction(c, a), a], exp, 1, show=fmt)


def afim_dois_pontos(b):
    r = b.rng
    a, c = r.choice([-3, -2, -1, 1, 2, 3, 4]), r.randint(-6, 8)
    x1, x2 = r.sample(range(-3, 6), 2)
    k = r.randint(6, 12)
    f = lambda x: a * x + c
    stem = (f"O gráfico de uma função afim passa pelos pontos \\(({x1}, {f(x1)})\\) e \\(({x2}, {f(x2)})\\). "
            f"Qual é o valor dessa função em \\(x = {k}\\)?")
    exp = (f"**1. Inclinação:** \\(a = \\dfrac{{\\Delta y}}{{\\Delta x}} = \\dfrac{{{f(x2)} - ({f(x1)})}}{{{x2} - ({x1})}} = {a}\\).\n\n"
           f"**2. Coeficiente linear:** use um dos pontos em \\(y = ax + b\\): \\({f(x1)} = {a}\\cdot({x1}) + b\\), logo \\(b = {c}\\).\n\n"
           f"**3. Calcule:** \\(f({k}) = {a}\\cdot{k} + ({c}) = {f(k)}\\).")
    return b.make(stem, f(k), [a * k, f(k) - c + x1, -f(k), f(x2) + (k - x2)], exp, 2, show=fmt)


def quad_vertice(b):
    r = b.rng
    a = r.choice([-3, -2, -1, 1, 2, 3])
    xv, yv = r.randint(-5, 6), r.randint(-12, 12)
    bb, c = -2 * a * xv, a * xv * xv + yv
    kind = "mínimo" if a > 0 else "máximo"
    stem = (f"A função \\(f(x) = {a if abs(a) != 1 else ('-' if a < 0 else '')}x^2 {'+' if bb >= 0 else '-'} {abs(bb)}x {'+' if c >= 0 else '-'} {abs(c)}\\) "
            f"tem valor {kind}. Qual é esse valor?")
    exp = (f"Como \\(a = {a}\\) é {'positivo, a parábola abre para cima e tem mínimo' if a > 0 else 'negativo, a parábola abre para baixo e tem máximo'}.\n\n"
           f"\\[x_v = -\\dfrac{{b}}{{2a}} = -\\dfrac{{{bb}}}{{2\\cdot({a})}} = {xv}\\]\n\n"
           f"O valor {kind} é \\(f(x_v) = f({xv}) = {yv}\\).\n\n"
           f"*Erro comum:* responder \\(x_v = {xv}\\), que é **onde** o {kind} acontece, e não o valor dele.")
    return b.make(stem, yv, [xv, -yv, c, yv + a], exp, 2, show=fmt)


RT_DIRECT = [
    ("Uma receita usa {a} xícaras de farinha para {b} pessoas. Quantas xícaras são necessárias para {c} pessoas?", "xícaras"),
    ("Um carro percorre {a} km com {b} litros de gasolina. Quantos quilômetros percorre com {c} litros?", "km"),
    ("Uma impressora imprime {a} páginas em {b} minutos. Quantas páginas imprime em {c} minutos?", "páginas"),
]


def regra_tres_direta(b):
    r = b.rng
    tpl, unit = r.choice(RT_DIRECT)
    per = r.choice([2, 3, 4, 5, 6, 8, 12, 15])
    bq, cq = r.sample([2, 3, 4, 5, 6, 8, 10, 12], 2)
    a, ans = per * bq, per * cq
    stem = tpl.format(a=a, b=bq, c=cq)
    exp = (f"As grandezas são **diretamente proporcionais**: dobrando uma, dobra a outra. Monte a proporção:\n\n"
           f"\\[\\dfrac{{{a}}}{{{bq}}} = \\dfrac{{x}}{{{cq}}} \\Rightarrow x = \\dfrac{{{a}\\cdot{cq}}}{{{bq}}} = {ans}\\]\n\n"
           f"Outro jeito: por unidade dá \\({a} \\div {bq} = {per}\\), e \\({per}\\cdot{cq} = {ans}\\).")
    return b.make(stem, ans, [Fraction(a * bq, cq), a + cq - bq, a * cq, per + cq], exp, 1, show=lambda v: fmt(v, unit))


def regra_tres_inversa(b):
    r = b.rng
    work = r.choice([12, 24, 30, 36, 48, 60, 72])
    w1 = r.choice([d for d in (2, 3, 4, 6, 8, 12) if work % d == 0])
    w2 = r.choice([d for d in (2, 3, 4, 6, 8, 12) if work % d == 0 and d != w1])
    d1, d2 = work // w1, work // w2
    stem = f"{w1} pedreiros constroem um muro em {d1} dias. Trabalhando no mesmo ritmo, em quantos dias {w2} pedreiros constroem o mesmo muro?"
    exp = (f"Mais pedreiros terminam **mais rápido**: as grandezas são **inversamente proporcionais**, então o produto é constante:\n\n"
           f"\\[{w1}\\cdot{d1} = {w2}\\cdot x \\Rightarrow x = \\dfrac{{{w1 * d1}}}{{{w2}}} = {d2}\\]\n\n"
           f"*Erro comum:* montar como direta, o que daria \\({Fraction(d1 * w2, w1)}\\) dias (mais pedreiros levando mais tempo não faz sentido).")
    return b.make(stem, d2, [Fraction(d1 * w2, w1), d1, d1 + w1 - w2, w1 * d1], exp, 2, show=lambda v: fmt(v, "dias"))


def porcentagem_de(b):
    r = b.rng
    p = r.choice([5, 10, 12, 15, 20, 25, 30, 40, 45, 60, 75])
    n = r.choice([40, 60, 80, 120, 150, 200, 240, 300, 360, 400, 500, 800, 1200])
    ans = Fraction(p * n, 100)
    stem = f"Numa escola com {n} alunos, {p}% praticam algum esporte. Quantos alunos praticam esporte?"
    exp = (f"\\({p}\\%\\) significa \\(\\dfrac{{{p}}}{{100}}\\). Então:\n\n\\[\\dfrac{{{p}}}{{100}}\\cdot{n} = {fmt(ans)}\\]\n\n"
           f"Dica de cálculo mental: 10% de {n} é {fmt(Fraction(n, 10))}.")
    return b.make(stem, ans, [Fraction(n, p) if n % p == 0 else Fraction(n * 10, p), p * n // 10, n - ans, Fraction(p * n, 10)], exp, 1,
                  show=lambda v: f"{fmt(v)} alunos")


def aumento_desconto(b):
    r = b.rng
    price = r.choice([80, 120, 150, 200, 250, 300, 400, 500, 800])
    p1, p2 = r.choice([10, 20, 25, 30]), r.choice([10, 20, 25, 30])
    final = Fraction(price) * Fraction(100 + p1, 100) * Fraction(100 - p2, 100)
    stem = f"Um produto custava {money(price)}. Teve um aumento de {p1}% e, depois, um desconto de {p2}% sobre o novo preço. Qual é o preço final?"
    exp = (f"Aumentar \\({p1}\\%\\) é multiplicar por \\({fmt(Fraction(100 + p1, 100))}\\); descontar \\({p2}\\%\\) é multiplicar por \\({fmt(Fraction(100 - p2, 100))}\\).\n\n"
           f"\\[{price}\\cdot{fmt(Fraction(100 + p1, 100))}\\cdot{fmt(Fraction(100 - p2, 100))} = {fmt(float(final))}\\]\n\n"
           f"*Erro comum:* fazer \\({p1}\\% - {p2}\\%\\) direto. Os percentuais se aplicam sobre valores diferentes, então **multiplicam**, não somam.")
    naive = Fraction(price) * Fraction(100 + p1 - p2, 100)
    return b.make(stem, final, [naive, Fraction(price) * Fraction(100 - p1, 100) * Fraction(100 + p2, 100), Fraction(price) * Fraction(100 + p1, 100), price + p1 - p2],
                  exp, 2, show=lambda v: money(float(v)))


def juros(b):
    r = b.rng
    c = r.choice([1000, 2000, 5000, 10000])
    i, t = r.choice([5, 10, 20]), r.choice([2, 3])
    compound = r.random() < 0.5
    if compound:
        m = Fraction(c) * Fraction(100 + i, 100) ** t
        stem = f"Um capital de {money(c)} foi aplicado a juros compostos de {i}% ao mês. Qual é o montante após {t} meses?"
        exp = (f"Juros compostos: \\(M = C(1 + i)^t\\).\n\n\\[M = {c}\\cdot({fmt(Fraction(100 + i, 100))})^{t} = {fmt(float(m))}\\]\n\n"
               f"*Erro comum:* calcular como juros simples ({money(c * (1 + i * t / 100))}), sem os juros sobre juros.")
        wrong = [Fraction(c) * (1 + Fraction(i * t, 100)), Fraction(c) * Fraction(i, 100) ** t, Fraction(c) * Fraction(100 + i, 100), m - c]
        return b.make(stem, m, wrong, exp, 2, show=lambda v: money(float(v)))
    j = Fraction(c * i * t, 100)
    stem = f"Um capital de {money(c)} foi aplicado a juros simples de {i}% ao mês durante {t} meses. Quanto rendeu de juros?"
    exp = f"Juros simples: \\(J = C\\cdot i\\cdot t = {c}\\cdot{fmt(Fraction(i, 100))}\\cdot{t} = {fmt(j)}\\).\n\n*Atenção:* a pergunta é pelos juros, não pelo montante ({money(float(c + j))})."
    return b.make(stem, j, [c + j, Fraction(c * i, 100), j * t, Fraction(c) * Fraction(100 + i, 100) ** t - c], exp, 1, show=lambda v: money(float(v)))


def mmc_problema(b):
    r = b.rng
    a, c = r.sample([4, 6, 8, 9, 10, 12, 15, 18, 20], 2)
    l = a * c // math.gcd(a, c)
    stem = f"Dois ônibus saem juntos do terminal às 6h. Um parte a cada {a} minutos e o outro a cada {c} minutos. Depois de quantos minutos eles voltam a sair juntos pela primeira vez?"
    exp = (f"Eles saem juntos em minutos que são múltiplos de {a} **e** de {c} ao mesmo tempo: o primeiro é o **MMC**.\n\n"
           f"\\[\\text{{MMC}}({a}, {c}) = {l}\\]\n\n*Erro comum:* multiplicar \\({a}\\cdot{c} = {a * c}\\), que é um múltiplo comum, mas não necessariamente o menor.")
    return b.make(stem, l, [a * c, math.gcd(a, c), a + c, max(a, c)], exp, 2, show=lambda v: fmt(v, "minutos"))


def mdc_problema(b):
    r = b.rng
    g = r.choice([6, 8, 10, 12, 15, 20])
    m1, m2 = r.sample([3, 4, 5, 7, 9, 11], 2)
    a, c = g * m1, g * m2
    stem = f"Duas fitas medem {a} cm e {c} cm. Quero cortá-las em pedaços todos do mesmo tamanho, o maior possível, sem sobras. Qual deve ser o tamanho de cada pedaço?"
    exp = (f"O tamanho precisa dividir {a} e {c} ao mesmo tempo, e ser o maior possível: é o **MDC**.\n\n\\[\\text{{MDC}}({a}, {c}) = {g}\\]\n\n"
           f"Serão \\({m1} + {m2} = {m1 + m2}\\) pedaços de {g} cm.")
    return b.make(stem, g, [a * c // g, m1 + m2, g // 2 if g % 2 == 0 else g * 2, abs(a - c)], exp, 2, show=lambda v: fmt(v, "cm"))


def potencias(b):
    r = b.rng
    base = r.choice([2, 3, 5, 10])
    m, n, p = r.randint(2, 9), r.randint(2, 9), r.randint(1, 6)
    e = m + n - p
    stem = f"Simplificando \\(\\dfrac{{{base}^{{{m}}}\\cdot{base}^{{{n}}}}}{{{base}^{{{p}}}}}\\), obtemos:"
    exp = (f"Na multiplicação de mesma base, **somam-se** os expoentes; na divisão, **subtraem-se**:\n\n"
           f"\\[{base}^{{{m} + {n} - {p}}} = {base}^{{{e}}}\\]\n\n*Erro comum:* multiplicar os expoentes (\\({m}\\cdot{n}\\)), o que vale para potência de potência.")
    show = lambda v: f"\\({base}^{{{v}}}\\)"
    return b.make(stem, e, [m * n - p, m + n + p, Fraction(m * n, p) if (m * n) % p == 0 else m * n, e + 1], exp, 1, show=show)


def pa(b):
    r = b.rng
    a1, d, n = r.randint(-5, 12), r.choice([-4, -3, 2, 3, 4, 5, 7]), r.randint(8, 30)
    an = a1 + (n - 1) * d
    seq = ", ".join(str(a1 + k * d) for k in range(4))
    if r.random() < 0.5:
        stem = f"Qual é o {n}º termo da progressão aritmética \\(({seq}, \\ldots)\\)?"
        exp = (f"Razão: \\(r = {a1 + d} - ({a1}) = {d}\\). Termo geral: \\(a_n = a_1 + (n - 1)r\\).\n\n\\[a_{{{n}}} = {a1} + {n - 1}\\cdot({d}) = {an}\\]\n\n"
               f"*Erro comum:* usar \\(n\\) no lugar de \\(n - 1\\), o que daria \\({a1 + n * d}\\).")
        return b.make(stem, an, [a1 + n * d, a1 * n * d, an - d * 2, n * d], exp, 1, show=fmt)
    s = (a1 + an) * n // 2 if (a1 + an) * n % 2 == 0 else Fraction((a1 + an) * n, 2)
    stem = f"Qual é a soma dos {n} primeiros termos da progressão aritmética \\(({seq}, \\ldots)\\)?"
    exp = (f"Primeiro o último termo: \\(a_{{{n}}} = {a1} + {n - 1}\\cdot({d}) = {an}\\).\n\n"
           f"Soma da PA: \\(S_n = \\dfrac{{(a_1 + a_n)\\,n}}{{2}} = \\dfrac{{({a1} + {an})\\cdot{n}}}{{2}} = {fmt(s)}\\).")
    return b.make(stem, s, [(a1 + an) * n, an * n, Fraction((a1 + a1 + n * d) * n, 2), a1 + an], exp, 2, show=fmt)


def pg(b):
    r = b.rng
    a1, q, n = r.choice([1, 2, 3, 5]), r.choice([2, 3]), r.randint(5, 8)
    an = a1 * q ** (n - 1)
    seq = ", ".join(str(a1 * q ** k) for k in range(4))
    stem = f"Qual é o {n}º termo da progressão geométrica \\(({seq}, \\ldots)\\)?"
    exp = (f"Razão: \\(q = {a1 * q} \\div {a1} = {q}\\). Termo geral: \\(a_n = a_1\\cdot q^{{n - 1}}\\).\n\n\\[a_{{{n}}} = {a1}\\cdot{q}^{{{n - 1}}} = {an}\\]")
    return b.make(stem, an, [a1 * q ** n, a1 + (n - 1) * q, a1 * q * (n - 1), an // q], exp, 1, show=fmt)


def log_basico(b):
    r = b.rng
    base = r.choice([2, 3, 5, 10])
    k = r.randint(-2, 5)
    val = Fraction(base) ** k
    arg = fmt(val).replace("\\(", "").replace("\\)", "") if val.denominator != 1 else str(val.numerator)
    stem = f"Qual é o valor de \\(\\log_{{{base}}} {arg}\\)?"
    exp = (f"\\(\\log_{{{base}}} {arg} = x\\) significa \\({base}^x = {arg}\\). Como \\({base}^{{{k}}} = {arg}\\), temos \\(x = {k}\\).\n\n"
           "Pergunta-chave do logaritmo: *a que expoente devo elevar a base para obter o número?*")
    return b.make(stem, k, [-k, Fraction(val.numerator, base) if val.denominator == 1 else k + 1, base * k, k + 1], exp, 1, show=fmt)


def log_propriedades(b):
    r = b.rng
    a, c = r.sample([2, 3, 5, 7], 2)
    la, lc = {2: "0,30", 3: "0,48", 5: "0,70", 7: "0,85"}[a], {2: "0,30", 3: "0,48", 5: "0,70", 7: "0,85"}[c]
    fa, fc = {2: 0.30, 3: 0.48, 5: 0.70, 7: 0.85}[a], {2: 0.30, 3: 0.48, 5: 0.70, 7: 0.85}[c]
    pa_, pc = r.randint(1, 3), r.randint(1, 2)
    n = a ** pa_ * c ** pc
    ans = round(pa_ * fa + pc * fc, 2)
    stem = f"Sabendo que \\(\\log {a} = {la}\\) e \\(\\log {c} = {lc}\\), qual é o valor de \\(\\log {n}\\)?"
    exp = (f"Fatore: \\({n} = {a}^{{{pa_}}}\\cdot{c}^{{{pc}}}\\). Use \\(\\log(xy) = \\log x + \\log y\\) e \\(\\log x^k = k\\log x\\):\n\n"
           f"\\[\\log {n} = {pa_}\\cdot{la} + {pc}\\cdot{lc} = {fmt(ans)}\\]\n\n*Erro comum:* multiplicar os logaritmos em vez de somar.")
    return b.make(stem, ans, [round(fa * fc * pa_ * pc, 2), round(fa + fc, 2), round(pa_ * fa * pc * fc, 3), round(ans + 0.3, 2)], exp, 2,
                  show=lambda v: fmt(float(v)))


TRIPLES = [(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (6, 8, 10), (9, 12, 15)]


def pitagoras(b):
    r = b.rng
    a, c, h = r.choice(TRIPLES)
    k = r.choice([1, 2, 3])
    a, c, h = a * k, c * k, h * k
    if r.random() < 0.5:
        stem = f"Os catetos de um triângulo retângulo medem {a} cm e {c} cm. Quanto mede a hipotenusa?"
        exp = f"Pitágoras: \\(h^2 = {a}^2 + {c}^2 = {a * a} + {c * c} = {h * h}\\), logo \\(h = {h}\\) cm.\n\n*Erro comum:* somar os catetos (\\({a + c}\\)) em vez de seus quadrados."
        return b.make(stem, h, [a + c, a * c // 2, h * h, abs(c - a) + h // 2], exp, 1, show=lambda v: fmt(v, "cm"))
    stem = f"Uma escada de {h} m está apoiada num muro, com o pé a {a} m da base do muro. A que altura do chão a escada toca o muro?"
    exp = (f"Muro, chão e escada formam um triângulo retângulo; a escada é a hipotenusa.\n\n\\[x^2 + {a}^2 = {h}^2 \\Rightarrow x^2 = {h * h} - {a * a} = {c * c} \\Rightarrow x = {c}\\text{{ m}}\\]\n\n"
           "*Erro comum:* somar os quadrados quando o que falta é um cateto.")
    return b.make(stem, c, [h - a, h + a, math.isqrt(h * h + a * a) if math.isqrt(h * h + a * a) ** 2 == h * h + a * a else h + a // 2, c * c], exp, 1,
                  show=lambda v: fmt(v, "m"))


def areas(b):
    r = b.rng
    kind = r.choice(["ret", "tri", "trap"])
    if kind == "ret":
        w, h = r.randint(3, 20), r.randint(3, 20)
        stem = f"Um terreno retangular mede {w} m por {h} m. Qual é a sua área?"
        exp = f"Área do retângulo: base × altura \\(= {w}\\cdot{h} = {w * h}\\text{{ m}}^2\\).\n\n*Erro comum:* calcular o perímetro (\\(2\\cdot({w} + {h}) = {2 * (w + h)}\\) m), que é o contorno, não a superfície."
        return b.make(stem, w * h, [2 * (w + h), w + h, w * h // 2, (w * h) * 2], exp, 1, show=lambda v: f"\\({v}\\text{{ m}}^2\\)")
    if kind == "tri":
        base, h = r.randint(2, 15) * 2, r.randint(3, 20)
        stem = f"Um triângulo tem base {base} cm e altura {h} cm. Qual é a sua área?"
        exp = f"Área do triângulo: \\(\\dfrac{{\\text{{base}}\\cdot\\text{{altura}}}}{{2}} = \\dfrac{{{base}\\cdot{h}}}{{2}} = {base * h // 2}\\text{{ cm}}^2\\).\n\n*Erro comum:* esquecer de dividir por 2."
        return b.make(stem, base * h // 2, [base * h, base + h, base * h // 4 if base * h % 4 == 0 else base * h * 2, base * h // 2 + h], exp, 1,
                      show=lambda v: f"\\({v}\\text{{ cm}}^2\\)")
    B, bb, h = r.randint(8, 20), r.randint(2, 7), r.randint(2, 10) * 2
    area = (B + bb) * h // 2
    stem = f"Um trapézio tem bases de {B} cm e {bb} cm e altura de {h} cm. Qual é a sua área?"
    exp = f"Área do trapézio: \\(\\dfrac{{(B + b)\\cdot h}}{{2}} = \\dfrac{{({B} + {bb})\\cdot{h}}}{{2}} = {area}\\text{{ cm}}^2\\)."
    return b.make(stem, area, [(B + bb) * h, B * bb * h // 2, B * h, (B - bb) * h // 2], exp, 1, show=lambda v: f"\\({v}\\text{{ cm}}^2\\)")


def volumes(b):
    r = b.rng
    if r.random() < 0.5:
        a, c, h = r.randint(2, 10), r.randint(2, 10), r.randint(2, 10)
        v = a * c * h
        stem = f"Uma caixa d'água tem a forma de um paralelepípedo de {a} m × {c} m × {h} m. Quantos litros ela comporta quando cheia?"
        exp = (f"Volume = comprimento × largura × altura \\(= {a}\\cdot{c}\\cdot{h} = {v}\\text{{ m}}^3\\).\n\n"
               f"Como \\(1\\text{{ m}}^3 = 1000\\) litros: \\({v}\\cdot1000 = {fmt(v * 1000)}\\) litros.\n\n*Erro comum:* esquecer a conversão de m³ para litros.")
        return b.make(stem, v * 1000, [v, v * 100, v * 10000, 2 * (a * c + a * h + c * h) * 1000], exp, 2, show=lambda v_: fmt(v_, "litros"))
    rr, h = r.randint(1, 6), r.randint(2, 12)
    stem = f"Um cilindro tem raio da base {rr} cm e altura {h} cm. Qual é o seu volume? (Deixe em função de \\(\\pi\\).)"
    exp = (f"Volume do cilindro = área da base × altura \\(= \\pi r^2 h = \\pi\\cdot{rr}^2\\cdot{h} = {rr * rr * h}\\pi\\text{{ cm}}^3\\).\n\n"
           "*Erro comum:* usar \\(2\\pi r\\) (comprimento da circunferência) no lugar da área da base.")
    return b.make(stem, rr * rr * h, [2 * rr * h, rr * h, rr * rr * h * 2, rr * rr * h // 3 if rr * rr * h % 3 == 0 else rr * h * 2], exp, 1,
                  show=lambda v: f"\\({v}\\pi\\text{{ cm}}^3\\)")


def probabilidade(b):
    r = b.rng
    colors = r.sample(["azuis", "vermelhas", "verdes", "amarelas", "pretas"], 3)
    counts = [r.randint(2, 9) for _ in colors]
    total = sum(counts)
    target = r.randrange(3)
    p = Fraction(counts[target], total)
    stem = (f"Uma urna tem {counts[0]} bolas {colors[0]}, {counts[1]} {colors[1]} e {counts[2]} {colors[2]}. "
            f"Retirando uma bola ao acaso, qual é a probabilidade de ela ser {colors[target][:-1]}?")
    exp = (f"Probabilidade = casos favoráveis ÷ casos possíveis.\n\nFavoráveis: {counts[target]} bolas {colors[target]}. Possíveis: \\({' + '.join(map(str, counts))} = {total}\\).\n\n"
           f"\\[P = \\dfrac{{{counts[target]}}}{{{total}}}{' = ' + fmt(p).strip(chr(92) + '()') if p != Fraction(counts[target], total) or p.denominator != total else ''}\\]\n\n"
           "*Erro comum:* dividir pelo número de bolas de outra cor em vez do total.")
    others = [c for k, c in enumerate(counts) if k != target]
    wrong = [Fraction(counts[target], sum(others)), Fraction(1, 3), Fraction(sum(others), total), Fraction(counts[target], total + 1)]
    show = lambda v: f"\\(\\dfrac{{{v.numerator}}}{{{v.denominator}}}\\)" if v.denominator != 1 else str(v.numerator)
    return b.make(stem, p, wrong, exp, 1, show=show)


def media_mediana(b):
    r = b.rng
    n = r.choice([5, 7])
    vals = sorted(r.randint(2, 20) for _ in range(n))
    while len(set(vals)) < 3:
        vals = sorted(r.randint(2, 20) for _ in range(n))
    shown = vals[:]
    r.shuffle(shown)
    if r.random() < 0.5:
        mean = Fraction(sum(vals), n)
        stem = f"As notas de um aluno foram: {', '.join(map(str, shown))}. Qual é a média aritmética dessas notas?"
        exp = f"Some tudo e divida pela quantidade: \\(\\dfrac{{{' + '.join(map(str, shown))}}}{{{n}}} = \\dfrac{{{sum(vals)}}}{{{n}}} = {fmt(float(mean))}\\)."
        return b.make(stem, mean, [vals[n // 2], Fraction(sum(vals), n - 1), Fraction(vals[0] + vals[-1], 2), Fraction(sum(vals), n) + 1], exp, 1,
                      show=lambda v: fmt(round(float(v), 2)))
    med = vals[n // 2]
    stem = f"Qual é a mediana do conjunto de dados {', '.join(map(str, shown))}?"
    exp = (f"Primeiro **coloque em ordem**: {', '.join(map(str, vals))}. Com {n} valores, a mediana é o do meio (o {n // 2 + 1}º): **{med}**.\n\n"
           f"*Erro comum:* pegar o valor do meio sem ordenar, o que daria {shown[n // 2]}.")
    return b.make(stem, med, [shown[n // 2], round(sum(vals) / n, 1), max(set(vals), key=vals.count), vals[n // 2 - 1]], exp, 1, show=lambda v: fmt(v))


def combinatoria(b):
    r = b.rng
    if r.random() < 0.5:
        c, s_, t = r.randint(2, 6), r.randint(2, 5), r.randint(2, 4)
        stem = f"Maria tem {c} camisetas, {s_} saias e {t} pares de sapato. De quantas maneiras diferentes ela pode se vestir usando uma peça de cada tipo?"
        exp = f"Princípio fundamental da contagem: escolhas independentes se **multiplicam**: \\({c}\\cdot{s_}\\cdot{t} = {c * s_ * t}\\).\n\n*Erro comum:* somar (\\({c + s_ + t}\\))."
        return b.make(stem, c * s_ * t, [c + s_ + t, c * s_ + t, math.factorial(c + s_ + t) // 1000 or 7, c * s_], exp, 1, show=lambda v: fmt(v, "maneiras"))
    n = r.randint(5, 12)
    stem = f"Numa reunião com {n} pessoas, cada uma cumprimentou todas as outras uma única vez com um aperto de mão. Quantos apertos de mão houve?"
    exp = (f"Cada aperto envolve 2 pessoas e a ordem não importa (A com B é o mesmo que B com A): é uma **combinação**.\n\n"
           f"\\[C_{{{n},2}} = \\dfrac{{{n}\\cdot{n - 1}}}{{2}} = {n * (n - 1) // 2}\\]\n\n*Erro comum:* fazer \\({n}\\cdot{n - 1} = {n * (n - 1)}\\), contando cada aperto duas vezes.")
    return b.make(stem, n * (n - 1) // 2, [n * (n - 1), n * n, n * (n + 1) // 2, 2 * n], exp, 2, show=fmt)


def trig_notaveis(b):
    r = b.rng
    ang = r.choice([30, 60])
    h = r.choice([4, 6, 8, 10, 12, 20])
    opp = Fraction(h, 2) if ang == 30 else None
    if ang == 30:
        stem = f"Num triângulo retângulo, a hipotenusa mede {h} cm e um dos ângulos agudos mede 30°. Quanto mede o cateto oposto a esse ângulo?"
        exp = f"\\(\\sin 30° = \\dfrac{{\\text{{oposto}}}}{{\\text{{hipotenusa}}}}\\), e \\(\\sin 30° = \\dfrac12\\). Então oposto \\(= {h}\\cdot\\dfrac12 = {h // 2}\\) cm."
        return b.make(stem, h // 2, [h * 2, h, h - 2, h // 4 if h % 4 == 0 else h + 1], exp, 1, show=lambda v: fmt(v, "cm"))
    stem = f"Num triângulo retângulo, a hipotenusa mede {h} cm e um dos ângulos agudos mede 60°. Quanto mede o cateto adjacente a esse ângulo?"
    exp = f"\\(\\cos 60° = \\dfrac{{\\text{{adjacente}}}}{{\\text{{hipotenusa}}}} = \\dfrac12\\). Então adjacente \\(= {h}\\cdot\\dfrac12 = {h // 2}\\) cm.\n\n*Erro comum:* usar o seno no lugar do cosseno."
    return b.make(stem, h // 2, [h, h * 2, h - 1, h // 2 + 2], exp, 1, show=lambda v: fmt(v, "cm"))


def conversao(b):
    r = b.rng
    v = r.choice([18, 36, 54, 72, 90, 108, 144])
    stem = f"Um carro está a {v} km/h. Qual é essa velocidade em metros por segundo?"
    exp = f"1 km = 1000 m e 1 h = 3600 s, então para passar de km/h para m/s divide-se por **3,6**:\n\n\\[{v} \\div 3{{,}}6 = {v * 10 // 36}\\text{{ m/s}}\\]\n\n*Erro comum:* multiplicar por 3,6 (isso é o caminho de m/s para km/h)."
    return b.make(stem, v * 10 // 36, [round(v * 3.6, 1), v // 60 if v % 60 == 0 else round(v / 60, 1), v * 1000 // 60, v // 2], exp, 1,
                  show=lambda x: fmt(x, "m/s"))


# ------------------------------------------------ álgebra: a sequência do livro
# equação (treino → problema → desafio), sistemas, inequação, 2º grau e função quadrática.
# Cada nível só usa o que veio antes: nada de inequação em equação nem de Bhaskara em 1º grau.

def eq1_mmc(b):
    r = b.rng
    p, q = r.sample([2, 3, 4, 5, 6], 2)
    m = p * q // math.gcd(p, q)
    x = m * r.randint(1, 6) * r.choice([1, 1, -1])
    c = Fraction(x, p) + Fraction(x, q)
    stem = f"Resolva a equação \\(\\dfrac{{x}}{{{p}}} + \\dfrac{{x}}{{{q}}} = {fmt(c)}\\)."
    k = m // p + m // q
    exp = (f"Multiplique **todos** os termos pelo MMC de {p} e {q}, que é {m}:\n\n"
           f"\\[{m // p}x + {m // q}x = {fmt(c * m)} \\Rightarrow {k}x = {fmt(c * m)} \\Rightarrow x = {x}\\]\n\n"
           f"*Erro comum:* somar os denominadores, como se \\(\\dfrac{{x}}{{{p}}} + \\dfrac{{x}}{{{q}}}\\) fosse \\(\\dfrac{{2x}}{{{p + q}}}\\).")
    wrong = [c * (p + q) / 2, c * m, Fraction(c * m, m // p + 1), -x]
    return b.make(stem, Fraction(x), wrong, exp, 1, show=show_x)


def eq1_idades(b):
    r = b.rng
    k1, k2 = r.choice([(3, 2), (4, 3), (5, 3), (4, 2), (5, 2)])
    # pai = k1·f hoje; daqui a n anos, pai + n = k2·(f + n)  →  f = n(k2 - 1)/(k1 - k2)
    while True:
        n = r.randint(2, 20)
        if (n * (k2 - 1)) % (k1 - k2) == 0:
            f = n * (k2 - 1) // (k1 - k2)
            if 3 <= f <= 20:
                break
    words = {2: "o dobro", 3: "o triplo", 4: "o quádruplo", 5: "o quíntuplo"}
    stem = (f"Hoje, a idade de um pai é {words[k1]} da idade do filho. Daqui a {n} anos, a idade do pai será "
            f"{words[k2]} da idade do filho. Qual é a idade atual do filho?")
    exp = (f"Seja \\(x\\) a idade do filho hoje; o pai tem \\({k1}x\\).\n\n"
           f"Daqui a {n} anos: filho \\(x + {n}\\), pai \\({k1}x + {n}\\). **Os dois envelhecem {n} anos.**\n\n"
           f"\\[{k1}x + {n} = {k2}(x + {n}) \\Rightarrow {k1}x + {n} = {k2}x + {k2 * n} \\Rightarrow {k1 - k2}x = {(k2 - 1) * n}\\Rightarrow x = {f}\\]\n\n"
           f"**Confira:** hoje {f} e {k1 * f}; daqui a {n} anos, {f + n} e {k1 * f + n}, e \\({k1 * f + n} = {k2}\\cdot{f + n}\\). ✔\n\n"
           f"*Erro comum:* somar os {n} anos só na idade de um deles.")
    wrong = [k1 * f, f + n, Fraction(k2 * n, k1 - k2), f * k2]
    return b.make(stem, f, wrong, exp, 3, show=lambda v: fmt(v, "anos"))


def eq1_restante(b):
    r = b.rng
    a, c = r.choice([(1, 3), (1, 4), (2, 5), (1, 5), (1, 2)]), r.choice([(1, 2), (1, 3), (2, 3), (1, 4), (3, 4)])
    fa, fc = Fraction(*a), Fraction(*c)
    left = (1 - fa) * (1 - fc)  # fração que sobra
    while True:
        total = r.randint(4, 40) * 30
        sobra = total * left
        if sobra.denominator == 1:
            break
    stem = (f"Ana gastou {a[0]}/{a[1]} do seu salário com aluguel e {c[0]}/{c[1]} do que **restou** com mercado. "
            f"Sobraram R$ {fmt(sobra)},00. Qual é o salário de Ana?")
    exp = (f"Seja \\(x\\) o salário. Depois do aluguel restam \\(\\left(1 - \\dfrac{{{a[0]}}}{{{a[1]}}}\\right)x = {fmt(1 - fa)}\\,x\\).\n\n"
           f"O mercado leva {c[0]}/{c[1]} **desse resto**, então sobram \\({fmt(1 - fc)}\\) dele: "
           f"\\({fmt(1 - fc)}\\cdot{fmt(1 - fa)}\\,x = {fmt(left)}\\,x\\).\n\n"
           f"\\[{fmt(left)}\\,x = {fmt(sobra)} \\Rightarrow x = {fmt(total)}\\]\n\n"
           f"*Erro comum:* calcular {c[0]}/{c[1]} do salário inteiro, e não do que restou.")
    wrong = [sobra / (1 - fa - fc) if fa + fc < 1 else total * 2, sobra / (1 - fa), sobra / (1 - fc), sobra * 2]
    return b.make(stem, total, wrong, exp, 3, show=money)


def eq1_ingressos(b):
    r = b.rng
    price, n = r.choice([20, 30, 40, 50, 60]), r.randint(40, 200)
    meia = r.randint(5, n - 5)
    inteira = n - meia
    total = inteira * price + meia * price // 2
    stem = (f"Um teatro vendeu {n} ingressos: inteiras a R$ {price},00 e meias a R$ {price // 2},00. "
            f"A arrecadação foi de R$ {fmt(total)},00. Quantas meias-entradas foram vendidas?")
    exp = (f"Seja \\(m\\) o número de meias; as inteiras são \\({n} - m\\).\n\n"
           f"\\[{price}({n} - m) + {price // 2}m = {total}\\]\n\\[{price * n} - {price}m + {price // 2}m = {total} \\Rightarrow {price // 2}m = {price * n - total} \\Rightarrow m = {meia}\\]\n\n"
           f"*Atalho:* se todos pagassem inteira seriam R$ {fmt(price * n)}; cada meia \"tira\" R$ {price // 2}. "
           f"Faltaram {fmt(price * n - total)}, então são \\({fmt(price * n - total)} \\div {price // 2} = {meia}\\) meias.")
    return b.make(stem, meia, [inteira, total // price, n - inteira // 2, meia * 2], exp, 2, show=lambda v: fmt(v, "meias"))


def eq1_multiplos(b):
    """no estilo do TQM: a soma de múltiplos consecutivos vira uma equação de uma incógnita só"""
    r = b.rng
    k, n = r.choice([3, 4, 5, 6, 7, 8, 9, 11]), r.choice([3, 3, 4])
    first = k * r.randint(2, 25)
    terms = [first + k * i for i in range(n)]
    total = sum(terms)
    words = {3: "três", 4: "quatro"}
    stem = f"A soma de {words[n]} múltiplos consecutivos de {k} é {total}. Qual é o maior deles?"
    inc = " + ".join(["x"] + [f"(x + {k * i})" for i in range(1, n)])
    exp = (f"Múltiplos consecutivos de {k} andam de {k} em {k}. Chamando o menor de \\(x\\):\n\n"
           f"\\[{inc} = {total} \\Rightarrow {n}x + {k * n * (n - 1) // 2} = {total} \\Rightarrow x = {first}\\]\n\n"
           f"Os números são {', '.join(map(str, terms))}; o maior é **{terms[-1]}**.\n\n"
           f"*Erro comum:* tratar como números consecutivos (de 1 em 1), ou responder o menor.")
    return b.make(stem, terms[-1], [first, total // n, terms[-1] + k, first + n - 1], exp, 2, show=fmt)


def eq1_fracionaria(b):
    """x no denominador: vira 1º grau multiplicando em cruz, mas a resposta não pode zerar denominador"""
    r = b.rng
    while True:
        p, q = r.sample(range(1, 8), 2)
        m, n = r.randint(-6, 6), r.randint(-6, 6)
        if m == n:
            continue
        # p/(x - m) = q/(x - n)  →  p(x - n) = q(x - m)  →  (p - q)x = pn - qm
        x = Fraction(p * n - q * m, p - q)
        if x.denominator == 1 and x not in (m, n) and abs(x) <= 30:
            break
    den = lambda c: f"x {'-' if c >= 0 else '+'} {abs(c)}" if c else "x"
    stem = f"Resolva a equação \\(\\dfrac{{{p}}}{{{den(m)}}} = \\dfrac{{{q}}}{{{den(n)}}}\\)."
    exp = (f"**Antes de tudo, as restrições:** os denominadores não podem ser zero, então \\(x \\ne {m}\\) e \\(x \\ne {n}\\).\n\n"
           f"Multiplique em cruz: \\({p}({den(n)}) = {q}({den(m)})\\)\n\n"
           f"\\[{p}x {'-' if p * n >= 0 else '+'} {abs(p * n)} = {q}x {'-' if q * m >= 0 else '+'} {abs(q * m)} \\Rightarrow {p - q}x = {p * n - q * m} \\Rightarrow x = {x}\\]\n\n"
           f"Como \\({x}\\) não é {m} nem {n}, a solução vale.\n\n"
           f"*Erro comum:* trocar os pares na multiplicação em cruz (\\({p}({den(m)}) = {q}({den(n)})\\)).")
    wrong = [Fraction(p * m - q * n, p - q), Fraction(p * n + q * m, p - q), Fraction(p * n - q * m, p + q), -x]
    return b.make(stem, x, wrong, exp, 3, show=show_x)


def sistema_2x2(b):
    r = b.rng
    x, y = r.randint(-5, 9), r.randint(-5, 9)
    a1, b1 = r.choice([1, 2, 3]), r.choice([1, 2, -1])
    a2, b2 = r.choice([1, 2, 3, 4]), r.choice([-1, -2, 1, 3])
    if a1 * b2 - a2 * b1 == 0:
        a2 += 1
    c1, c2 = a1 * x + b1 * y, a2 * x + b2 * y
    term = lambda a, v, first=False: (("" if a == 1 else "-" if a == -1 else str(a)) + v) if first else \
        ((" + " if a > 0 else " - ") + ("" if abs(a) == 1 else str(abs(a))) + v)
    eq = lambda a, bb, c: f"{term(a, 'x', True)}{term(bb, 'y')} = {c}"
    stem = f"Resolva o sistema \\(\\begin{{cases}} {eq(a1, b1, c1)} \\\\ {eq(a2, b2, c2)} \\end{{cases}}\\). Quanto vale \\(x + y\\)?"
    exp = (f"**Por adição:** multiplique as equações para igualar (com sinais opostos) os coeficientes de uma incógnita e some.\n\n"
           f"Multiplicando a 1ª por \\({b2}\\) e a 2ª por \\({-b1}\\), o \\(y\\) some: "
           f"\\({a1 * b2 - a2 * b1}x = {c1 * b2 - c2 * b1}\\), então \\(x = {x}\\).\n\n"
           f"Substituindo na 1ª: \\(y = {y}\\). Logo \\(x + y = {x + y}\\).\n\n"
           f"**Confira** nas duas equações: \\({a1}\\cdot({x}) + ({b1})\\cdot({y}) = {c1}\\) e \\({a2}\\cdot({x}) + ({b2})\\cdot({y}) = {c2}\\). ✔")
    return b.make(stem, x + y, [x - y, x * y, c1 + c2, -(x + y)], exp, 1, show=fmt)


def show_ineq(op, v):
    v = Fraction(v)
    num = str(v.numerator) if v.denominator == 1 else f"{'-' if v < 0 else ''}\\dfrac{{{abs(v.numerator)}}}{{{v.denominator}}}"
    return f"\\(x {op} {num}\\)"


FLIP = {">": "<", "<": ">", "\\ge": "\\le", "\\le": "\\ge"}


def ineq1_simples(b):
    r = b.rng
    a = r.choice([-5, -4, -3, -2, 2, 3, 4, 5])
    root = r.randint(-6, 8)
    c = r.randint(-9, 9)
    op = r.choice([">", "<", "\\ge", "\\le"])
    rhs = a * root + c
    stem = f"Resolva a inequação \\({a}x {'+' if c >= 0 else '-'} {abs(c)} {op} {rhs}\\)."
    final = op if a > 0 else FLIP[op]
    exp = (f"Passe o \\({c}\\) para o outro lado: \\({a}x {op} {rhs - c}\\).\n\n"
           f"Agora divida por \\({a}\\)" + (f". Como \\({a}\\) é **negativo**, o sinal **inverte**:" if a < 0 else " (positivo, o sinal fica igual):") +
           f"\n\n\\[x {final} \\dfrac{{{rhs - c}}}{{{a}}} = {root}\\]\n\n"
           + ("*Erro comum:* dividir por um número negativo e esquecer de inverter a desigualdade." if a < 0 else
              "*Erro comum:* trocar o sinal da desigualdade sem motivo: só se inverte ao multiplicar ou dividir por negativo."))
    correct = (final, root)
    wrong = [Why((FLIP[final], root), "O número está certo, mas o sentido da desigualdade não. " + (f"Ao dividir por \\({a}\\), que é negativo, o sinal **inverte**." if a < 0 else "Só se inverte ao dividir por número negativo, e aqui ele é positivo.")),
             Why((final, -root), "O sinal do número ficou trocado. Teste um valor da sua resposta na inequação original."),
             Why((op if a < 0 else FLIP[op], Fraction(rhs + c, a)), f"O \\({c}\\) mudou de lado sem trocar a operação."),
             Why((final, Fraction(rhs, a)), f"Faltou passar o \\({c}\\) para o outro lado antes de dividir.")]
    return b.make(stem, correct, wrong, exp, 1, show=lambda v: show_ineq(*v))


def ineq1_inteiros(b):
    r = b.rng
    lo, hi = sorted(r.sample(range(-8, 15), 2))
    if hi - lo < 3:
        hi = lo + r.randint(3, 8)
    k = r.choice([2, 3, 4])
    m = r.randint(-5, 5)
    # lo < (x - m)/k ... escrito como  k·lo + m < x ≤ k·hi + m
    left, right = k * lo + m, k * hi + m
    count = right - left  # inteiros em ]left, right]
    stem = (f"Quantos números inteiros satisfazem \\({lo} < \\dfrac{{x {'-' if m >= 0 else '+'} {abs(m)}}}{{{k}}} \\le {hi}\\)?")
    exp = (f"Trabalhe nos três \"lados\" ao mesmo tempo. Multiplique tudo por {k} (positivo, os sinais ficam):\n\n"
           f"\\[{k * lo} < x {'-' if m >= 0 else '+'} {abs(m)} \\le {k * hi}\\]\n\n"
           f"Some {m} em tudo: \\({left} < x \\le {right}\\).\n\n"
           f"São os inteiros de \\({left + 1}\\) a \\({right}\\): \\({right} - ({left}) = {count}\\) números.\n\n"
           f"*Erro comum:* contar \\({left}\\) também; com \\(<\\) ele não entra.")
    return b.make(stem, count, [count + 1, hi - lo, count - 1, (hi - lo) * k + 1], exp, 2, show=fmt)


def ineq1_planos(b):
    r = b.rng
    fa, va = r.choice([20, 30, 40, 50]), r.choice([2, 3, 4])
    vb = va + r.choice([1, 2])
    fb = fa - r.choice([10, 15, 20]) if fa > 20 else 5
    # A: fa + va·t ; B: fb + vb·t ; B fica mais caro quando fb + vb t > fa + va t → t > (fa - fb)/(vb - va)
    lim = Fraction(fa - fb, vb - va)
    first = math.floor(lim) + 1
    stem = (f"Uma operadora oferece dois planos de internet móvel por mês: o plano A cobra R$ {fa},00 fixos mais R$ {va},00 por GB usado; "
            f"o plano B cobra R$ {fb},00 fixos mais R$ {vb},00 por GB. A partir de quantos GB inteiros o plano A passa a ser **mais barato** que o B?")
    exp = (f"Com \\(g\\) GB: A custa \\({fa} + {va}g\\) e B custa \\({fb} + {vb}g\\). Queremos A < B:\n\n"
           f"\\[{fa} + {va}g < {fb} + {vb}g \\Rightarrow {fa - fb} < {vb - va}g \\Rightarrow g > {fmt(lim)}\\]\n\n"
           f"O primeiro inteiro maior que \\({fmt(lim)}\\) é \\({first}\\).\n\n"
           + (f"*Atenção:* em \\(g = {fmt(lim)}\\) os planos custam o mesmo, e a pergunta é \"mais barato\"." if lim.denominator == 1 else
              "*Erro comum:* arredondar para baixo; a desigualdade pede maior que o limite."))
    return b.make(stem, first, [math.floor(lim), first + 1, fa - fb, Fraction(fa, va)], exp, 2, show=lambda v: fmt(v, "GB"))


def eq2_incompleta(b):
    r = b.rng
    if r.random() < 0.5:
        a, k = r.choice([1, 2, 3, 4]), r.randint(2, 12)
        c = a * k * k
        stem = f"Resolva a equação \\({a if a > 1 else ''}x^2 - {c} = 0\\)."
        exp = (f"Sem o termo em \\(x\\), isole o \\(x^2\\): \\(x^2 = \\dfrac{{{c}}}{{{a}}} = {k * k}\\), então \\(x = \\pm\\sqrt{{{k * k}}} = \\pm {k}\\).\n\n"
               f"*Erro comum:* esquecer a raiz negativa: \\((-{k})^2\\) também dá \\({k * k}\\).")
        pair = lambda v: f"\\(x = {v}\\)" if isinstance(v, str) else f"\\(x = -{v}\\) ou \\(x = {v}\\)"
        return b.make(stem, k, [Why(f"{k}", f"Faltou a raiz negativa: \\((-{k})^2\\) também dá \\({k * k}\\)."),
                                Why(f"{c // 2}", "Dividiu por 2 em vez de tirar a raiz quadrada."),
                                Why(k * k, f"\\({k * k}\\) é o valor de \\(x^2\\). Ainda falta tirar a raiz."),
                                Why(f"-{k}", f"Faltou a raiz positiva: \\({k}^2\\) também dá \\({k * k}\\).")], exp, 1,
                      show=lambda v: pair(v) if not isinstance(v, str) else f"\\(x = {v}\\) apenas")
    a, k = r.choice([1, 2, 3]), r.choice([v for v in range(-9, 10) if v])
    bb = -a * k
    stem = f"Quais são as raízes de \\({a if a > 1 else ''}x^2 {'+' if bb > 0 else '-'} {abs(bb)}x = 0\\)?"
    exp = (f"Sem termo independente, coloque \\(x\\) em evidência: \\(x({a if a > 1 else ''}x {'+' if bb > 0 else '-'} {abs(bb)}) = 0\\).\n\n"
           f"Um produto é zero quando um dos fatores é zero: \\(x = 0\\) ou \\({a if a > 1 else ''}x {'+' if bb > 0 else '-'} {abs(bb)} = 0 \\Rightarrow x = {k}\\).\n\n"
           f"*Erro comum:* dividir tudo por \\(x\\) e perder a raiz \\(x = 0\\).")
    shows = lambda v: f"\\(x = {v[0]}\\) ou \\(x = {v[1]}\\)" if v[1] is not None else f"\\(x = {v[0]}\\) apenas"
    return b.make(stem, (0, k), [Why((k, None), "Perdeu a raiz \\(x = 0\\). Isso acontece ao dividir os dois lados por \\(x\\): é melhor colocar \\(x\\) em evidência."),
                                 Why((0, -k), "O sinal da segunda raiz ficou trocado. Substitua na equação para conferir."),
                                 Why((-k, None), "Perdeu a raiz \\(x = 0\\) e trocou o sinal da outra."),
                                 Why((0, bb), "Esse é o coeficiente \\(b\\), não a raiz. Iguale o fator a zero e isole \\(x\\).")], exp, 1, show=shows)


def eq2_soma_produto(b):
    r = b.rng
    x1, x2 = r.sample([v for v in range(-8, 10) if v], 2)
    a = r.choice([1, 1, 2, 3])
    s, p = x1 + x2, x1 * x2
    bb, c = -a * s, a * p
    ask = r.choice(["soma", "produto"])
    lead = "" if a == 1 else str(a)
    stem = (f"Sem resolver a equação \\({poly2(a, bb, c)} = 0\\), "
            f"qual é {'a' if ask == 'soma' else 'o'} {ask} das suas raízes?")
    ans = s if ask == "soma" else p
    exp = (f"Em \\(ax^2 + bx + c = 0\\): soma \\(= -\\dfrac{{b}}{{a}}\\) e produto \\(= \\dfrac{{c}}{{a}}\\). Aqui \\(a = {a}\\), \\(b = {bb}\\), \\(c = {c}\\):\n\n"
           f"\\[x_1 + x_2 = -\\dfrac{{{bb}}}{{{a}}} = {s} \\qquad x_1 x_2 = \\dfrac{{{c}}}{{{a}}} = {p}\\]\n\n"
           f"*Erro comum:* esquecer o sinal de menos na soma, ou não dividir por \\(a\\).")
    wrong = [Why(-ans, "O sinal ficou trocado: a soma é \\(-\\dfrac{b}{a}\\) (com o menos) e o produto é \\(\\dfrac{c}{a}\\)." if ask == "soma" else "O produto é \\(\\dfrac{c}{a}\\), sem trocar o sinal."),
             Why(bb if ask == "soma" else c, "Faltou dividir por \\(a\\)" + (" e trocar o sinal de \\(b\\)." if ask == "soma" else ".") if a != 1 else "Faltou trocar o sinal: soma \\(= -\\dfrac{b}{a}\\)."),
             Why(Fraction(c, a) if ask == "soma" else -Fraction(bb, a), "Esse é o " + ("produto" if ask == "soma" else "a soma") + ", não o que a pergunta pede."),
             Why(ans * a, "Multiplicou por \\(a\\) em vez de dividir.")]
    return b.make(stem, ans, wrong, exp, 1, show=fmt)


def eq2_area(b):
    r = b.rng
    w, d = r.randint(3, 15), r.randint(2, 8)
    area = w * (w + d)
    stem = f"Um terreno retangular tem {d} m a mais de comprimento do que de largura, e sua área é {area} m². Qual é a largura?"
    delta = d * d + 4 * area
    exp = (f"Largura \\(x\\), comprimento \\(x + {d}\\): \\(x(x + {d}) = {area} \\Rightarrow x^2 + {d}x - {area} = 0\\).\n\n"
           f"\\[\\Delta = {d}^2 + 4\\cdot{area} = {delta} \\qquad x = \\dfrac{{-{d} \\pm {math.isqrt(delta)}}}{{2}}\\]\n\n"
           f"As raízes são \\({w}\\) e \\({-(w + d)}\\); largura não é negativa, então \\(x = {w}\\) m.\n\n"
           f"*Erro comum:* responder o comprimento (\\({w + d}\\) m), ou aceitar a raiz negativa.")
    return b.make(stem, w, [w + d, Fraction(area, d), area // 2, w - 1 if w > 3 else w + 2], exp, 2, show=lambda v: fmt(v, "m"))


def quad_raizes_grafico(b):
    r = b.rng
    x1, x2 = sorted(r.sample([v for v in range(-7, 9)], 2))
    a = r.choice([1, -1])
    bb, c = -a * (x1 + x2), a * x1 * x2
    lead = "" if a == 1 else "-"
    stem = f"Em que pontos o gráfico de \\(f(x) = {poly2(a, bb, c)}\\) corta o eixo \\(x\\)?"
    exp = (f"Cortar o eixo \\(x\\) é ter \\(f(x) = 0\\). Resolva \\({lead}x^2 {'+' if bb >= 0 else '-'} {abs(bb)}x {'+' if c >= 0 else '-'} {abs(c)} = 0\\)"
           + (" (multiplique por \\(-1\\) para facilitar)" if a < 0 else "") +
           f": as raízes somam \\({x1 + x2}\\) e multiplicam \\({x1 * x2}\\), então são \\({x1}\\) e \\({x2}\\).\n\n"
           f"Os pontos são \\(({x1}, 0)\\) e \\(({x2}, 0)\\).\n\n*Erro comum:* confundir com o ponto onde corta o eixo \\(y\\), que é \\((0, {c})\\).")
    pts = lambda v: f"\\(({v[0]}, 0)\\) e \\(({v[1]}, 0)\\)" if v[0] != "y" else f"\\((0, {v[1]})\\) apenas"
    return b.make(stem, (x1, x2), [(-x2, -x1), ("y", c), (x1 + x2, x1 * x2), (-x1, x2)], exp, 1, show=pts)


def quad_valor(b):
    r = b.rng
    a, bb, c = r.choice([1, 2, -1, 3]), r.randint(-6, 6), r.randint(-9, 9)
    k = r.choice([-3, -2, -1, 2, 3, 4])
    y = a * k * k + bb * k + c
    lead = {1: "", -1: "-"}.get(a, str(a))
    stem = f"Dada \\(f(x) = {poly2(a, bb, c)}\\), quanto vale \\(f({k})\\)?"
    exp = (f"Troque \\(x\\) por \\(({k})\\), **com parênteses**:\n\n"
           f"\\[f({k}) = {lead}({k})^2 {'+' if bb >= 0 else '-'} {abs(bb)}\\cdot({k}) {'+' if c >= 0 else '-'} {abs(c)} = {a * k * k} {'+' if bb * k >= 0 else '-'} {abs(bb * k)} {'+' if c >= 0 else '-'} {abs(c)} = {y}\\]\n\n"
           f"*Erro comum:* fazer \\(-{abs(k)}^2 = -{k * k}\\). Com parênteses, \\(({k})^2 = {k * k}\\).")
    return b.make(stem, y, [-a * k * k + bb * k + c, a * k * k - bb * k + c, a * 2 * k + bb * k + c, y + a * k], exp, 1, show=fmt)


# ---------------------------------------------------------------- física

def mru(b):
    r = b.rng
    v, t = r.choice([20, 30, 40, 50, 60, 80, 90, 100]), r.choice([2, 3, 4, 5])
    if r.random() < 0.5:
        stem = f"Um ônibus viaja com velocidade constante de {v} km/h durante {t} horas. Que distância ele percorre?"
        exp = f"No movimento uniforme, \\(d = v\\cdot t = {v}\\cdot{t} = {v * t}\\text{{ km}}\\)."
        return b.make(stem, v * t, [v + t, Fraction(v, t), v * t * 2, v * (t - 1)], exp, 1, show=lambda x: fmt(x, "km"))
    d = v * t
    stem = f"Um ciclista percorre {d} km com velocidade constante de {v} km/h. Quanto tempo leva?"
    exp = f"\\(t = \\dfrac{{d}}{{v}} = \\dfrac{{{d}}}{{{v}}} = {t}\\text{{ h}}\\).\n\n*Erro comum:* multiplicar distância por velocidade."
    return b.make(stem, t, [d * v, Fraction(v, d), t + 1, Fraction(t, 2)], exp, 1, show=lambda x: fmt(x, "h"))


def mruv(b):
    r = b.rng
    v0, a, t = r.choice([0, 2, 4, 5, 10]), r.choice([2, 3, 4, 5]), r.randint(2, 8)
    if r.random() < 0.5:
        v = v0 + a * t
        stem = f"Um carro parte com velocidade de {v0} m/s e acelera uniformemente a {a} m/s² durante {t} s. Qual é sua velocidade final?"
        exp = f"\\(v = v_0 + a\\,t = {v0} + {a}\\cdot{t} = {v}\\text{{ m/s}}\\)."
        return b.make(stem, v, [a * t, v0 + a, v0 * a * t or v + 3, v + a], exp, 1, show=lambda x: fmt(x, "m/s"))
    v = v0 + a * t
    d = Fraction(v * v - v0 * v0, 2 * a)
    stem = f"Um móvel acelera uniformemente a {a} m/s², passando de {v0} m/s para {v} m/s. Que distância percorre nesse trecho?"
    exp = (f"Sem o tempo no enunciado, use **Torricelli**: \\(v^2 = v_0^2 + 2a\\,\\Delta s\\).\n\n"
           f"\\[{v}^2 = {v0}^2 + 2\\cdot{a}\\cdot\\Delta s \\Rightarrow \\Delta s = \\dfrac{{{v * v} - {v0 * v0}}}{{{2 * a}}} = {fmt(d)}\\text{{ m}}\\]")
    return b.make(stem, d, [Fraction(v * v, 2 * a), Fraction(v - v0, a), Fraction(v * v - v0 * v0, a), v * t], exp, 2, show=lambda x: fmt(x, "m"))


def newton(b):
    r = b.rng
    m, a = r.choice([2, 4, 5, 8, 10, 20, 50]), r.choice([2, 3, 4, 5])
    if r.random() < 0.6:
        stem = f"Uma força resultante age sobre um bloco de {m} kg e produz aceleração de {a} m/s². Qual é a intensidade dessa força?"
        exp = f"2ª lei de Newton: \\(F_R = m\\,a = {m}\\cdot{a} = {m * a}\\text{{ N}}\\)."
        return b.make(stem, m * a, [m + a, Fraction(m, a), m * a * 10, m * 10], exp, 1, show=lambda x: fmt(x, "N"))
    mu = r.choice([Fraction(1, 10), Fraction(1, 5), Fraction(3, 10)])
    f_at = mu * m * 10
    F = f_at + m * a
    stem = (f"Um bloco de {m} kg é puxado sobre uma mesa horizontal por uma força de {fmt(F)} N. O coeficiente de atrito cinético é "
            f"{fmt(float(mu))} e \\(g = 10\\text{{ m/s}}^2\\). Qual é a aceleração do bloco?")
    exp = (f"Atrito: \\(f_{{at}} = \\mu N = \\mu m g = {fmt(float(mu))}\\cdot{m}\\cdot10 = {fmt(f_at)}\\text{{ N}}\\).\n\n"
           f"Resultante: \\({fmt(F)} - {fmt(f_at)} = {m * a}\\text{{ N}}\\). Aceleração: \\(a = \\dfrac{{{m * a}}}{{{m}}} = {a}\\text{{ m/s}}^2\\).\n\n"
           "*Erro comum:* esquecer o atrito e dividir a força aplicada inteira pela massa.")
    return b.make(stem, a, [Fraction(F, m), Fraction(F + f_at, m), a + 1, Fraction(f_at, m)], exp, 2, show=lambda x: f"\\({fmt(x)}\\text{{ m/s}}^2\\)")


def energia(b):
    r = b.rng
    if r.random() < 0.5:
        m, v = r.choice([2, 4, 10, 50, 100]), r.choice([2, 4, 6, 10, 20])
        ec = m * v * v // 2
        stem = f"Qual é a energia cinética de um corpo de {m} kg que se move a {v} m/s?"
        exp = f"\\(E_c = \\dfrac{{m v^2}}{{2}} = \\dfrac{{{m}\\cdot{v}^2}}{{2}} = {ec}\\text{{ J}}\\).\n\n*Erro comum:* esquecer de elevar a velocidade ao quadrado."
        return b.make(stem, ec, [m * v // 2, m * v * v, m * v, ec * 2 + m], exp, 1, show=lambda x: fmt(x, "J"))
    h = r.choice([5, 20, 45, 80, 125])
    v = math.isqrt(20 * h)
    stem = f"Um objeto é abandonado do repouso a {h} m de altura. Desprezando a resistência do ar e usando \\(g = 10\\text{{ m/s}}^2\\), com que velocidade chega ao chão?"
    exp = (f"A energia potencial vira cinética: \\(mgh = \\dfrac{{mv^2}}{{2}}\\), e a massa se cancela.\n\n"
           f"\\[v = \\sqrt{{2gh}} = \\sqrt{{2\\cdot10\\cdot{h}}} = \\sqrt{{{20 * h}}} = {v}\\text{{ m/s}}\\]")
    return b.make(stem, v, [20 * h, 10 * h, math.isqrt(10 * h) if math.isqrt(10 * h) ** 2 == 10 * h else v // 2, h // 5 + v], exp, 2, show=lambda x: fmt(x, "m/s"))


def ohm(b):
    r = b.rng
    if r.random() < 0.5:
        R, i = r.choice([2, 4, 5, 10, 20, 50]), r.choice([2, 3, 4, 5, 10])
        stem = f"Um resistor de {R} Ω é percorrido por uma corrente de {i} A. Qual é a tensão entre seus terminais?"
        exp = f"Lei de Ohm: \\(U = R\\,i = {R}\\cdot{i} = {R * i}\\text{{ V}}\\)."
        return b.make(stem, R * i, [Fraction(R, i), R + i, Fraction(i, R), R * i * i], exp, 1, show=lambda x: fmt(x, "V"))
    r1, r2 = r.sample([2, 3, 4, 6, 12], 2)
    par = Fraction(r1 * r2, r1 + r2)
    stem = f"Dois resistores de {r1} Ω e {r2} Ω são ligados em paralelo. Qual é a resistência equivalente?"
    exp = (f"Em paralelo, \\(R_{{eq}} = \\dfrac{{R_1 R_2}}{{R_1 + R_2}} = \\dfrac{{{r1}\\cdot{r2}}}{{{r1} + {r2}}} = {fmt(par)}\\,\\Omega\\).\n\n"
           f"*Confira:* em paralelo o equivalente é sempre **menor** que o menor resistor. Somar (\\({r1 + r2}\\,\\Omega\\)) seria a ligação em série.")
    return b.make(stem, par, [r1 + r2, Fraction(r1 + r2, 2), Fraction(r1 * r2, abs(r1 - r2)), r1 * r2], exp, 2, show=lambda x: fmt(x, "Ω"))


def consumo(b):
    r = b.rng
    P = r.choice([1000, 2000, 3000, 4000, 5000, 6000])
    hrs, days = r.choice([Fraction(1, 2), Fraction(1, 3), 1, 2]), 30
    kwh = Fraction(P, 1000) * hrs * days
    price = r.choice([Fraction(1, 2), Fraction(4, 5), 1])
    cost = kwh * price
    stem = (f"Um chuveiro de {fmt(P)} W fica ligado {fmt(hrs) if isinstance(hrs, int) or hrs.denominator == 1 else ('meia hora' if hrs == Fraction(1, 2) else '20 minutos')} "
            f"{'hora' if hrs == 1 else 'horas' if isinstance(hrs, int) and hrs > 1 else ''} por dia, durante {days} dias. "
            f"Se o kWh custa {money(float(price))}, quanto custa esse consumo?")
    exp = (f"**1.** Potência em kW: \\({fmt(P)}\\text{{ W}} = {fmt(Fraction(P, 1000))}\\text{{ kW}}\\).\n\n"
           f"**2.** Energia: \\(E = P\\cdot\\Delta t = {fmt(Fraction(P, 1000))}\\cdot{fmt(float(hrs))}\\cdot{days} = {fmt(float(kwh))}\\text{{ kWh}}\\).\n\n"
           f"**3.** Custo: \\({fmt(float(kwh))}\\cdot{fmt(float(price))}\\) = {money(float(cost))}.\n\n*Erro comum:* esquecer de converter W para kW (o resultado fica mil vezes maior).")
    return b.make(stem, cost, [cost * 1000, kwh, cost / days, cost * 2], exp, 2, show=lambda x: money(float(x)))


def densidade_pressao(b):
    r = b.rng
    if r.random() < 0.5:
        m, v = r.choice([200, 300, 540, 780, 1000]), r.choice([100, 200, 250, 500])
        dens = Fraction(m, v)
        stem = f"Um objeto tem massa de {m} g e volume de {v} cm³. Qual é a sua densidade?"
        exp = f"\\(d = \\dfrac{{m}}{{V}} = \\dfrac{{{m}}}{{{v}}} = {fmt(float(dens))}\\text{{ g/cm}}^3\\). Se for maior que 1 g/cm³ (a da água), o objeto afunda na água."
        return b.make(stem, dens, [Fraction(v, m), m * v, Fraction(m, v) * 10, m - v], exp, 1, show=lambda x: f"\\({fmt(round(float(x), 3))}\\text{{ g/cm}}^3\\)")
    h = r.choice([5, 10, 20, 30, 40])
    p = 1000 * 10 * h
    stem = f"Qual é a pressão exercida apenas pela água a {h} m de profundidade? (Densidade da água 1000 kg/m³, \\(g = 10\\text{{ m/s}}^2\\).)"
    exp = (f"Stevin: \\(p = \\rho\\,g\\,h = 1000\\cdot10\\cdot{h} = {fmt(p)}\\text{{ Pa}}\\).\n\n"
           f"Isso equivale a cerca de {fmt(Fraction(h, 10))} atm (a cada 10 m de água, mais ou menos 1 atm).")
    return b.make(stem, p, [p // 10, p * 10, 1000 * h, p + 100000], exp, 2, show=lambda x: fmt(x, "Pa"))


def calor(b):
    r = b.rng
    m, dT = r.choice([100, 200, 250, 500, 1000]), r.choice([10, 20, 25, 30, 50])
    c = r.choice([(1, "água", "1 cal/g·°C"), (Fraction(1, 5), "alumínio", "0,2 cal/g·°C"), (Fraction(1, 10), "ferro", "0,1 cal/g·°C")])
    Q = c[0] * m * dT
    stem = f"Quanto calor é preciso fornecer a {m} g de {c[1]} (calor específico {c[2]}) para elevar sua temperatura em {dT} °C?"
    exp = f"Calor sensível: \\(Q = m\\,c\\,\\Delta T = {m}\\cdot{fmt(float(c[0]))}\\cdot{dT} = {fmt(Q)}\\text{{ cal}}\\)."
    return b.make(stem, Q, [m * dT, Q * 10, Fraction(m, dT), Q + m], exp, 1, show=lambda x: fmt(x, "cal"))


def ondas(b):
    r = b.rng
    lam, f = r.choice([Fraction(1, 2), 1, 2, 5, 10]), r.choice([10, 20, 50, 68, 100, 170])
    v = lam * f
    stem = f"Uma onda tem comprimento de onda de {fmt(float(lam))} m e frequência de {f} Hz. Qual é a sua velocidade de propagação?"
    exp = f"Equação fundamental: \\(v = \\lambda\\,f = {fmt(float(lam))}\\cdot{f} = {fmt(v)}\\text{{ m/s}}\\)."
    return b.make(stem, v, [Fraction(f, lam), Fraction(lam, f), f + lam, v * 2], exp, 1, show=lambda x: fmt(round(float(x), 3), "m/s"))


def temperatura(b):
    r = b.rng
    C = r.choice([-40, -10, 0, 10, 20, 25, 30, 35, 40, 100])
    F = Fraction(9 * C, 5) + 32
    stem = f"Uma temperatura de {C} °C corresponde a quantos graus Fahrenheit?"
    exp = f"\\(\\dfrac{{T_C}}{{5}} = \\dfrac{{T_F - 32}}{{9}} \\Rightarrow T_F = \\dfrac{{9\\cdot{C}}}{{5}} + 32 = {fmt(F)}\\text{{ °F}}\\)."
    return b.make(stem, F, [Fraction(9 * C, 5), C + 32, Fraction(5 * (C - 32), 9), C + 273], exp, 2, show=lambda x: fmt(round(float(x), 1), "°F"))


GENERATORS = [
    (eq1_simples, "mat", "mat-conjuntos-funcoes", "mat-equacao-1grau", 40),
    (eq1_dois_lados, "mat", "mat-conjuntos-funcoes", "mat-equacao-1grau", 30),
    (eq1_fracao, "mat", "mat-conjuntos-funcoes", "mat-equacao-1grau", 40),
    (eq1_parenteses, "mat", "mat-conjuntos-funcoes", "mat-equacao-1grau", 30),
    (eq1_consecutivos, "mat", "mat-conjuntos-funcoes", "mat-equacao-1grau", 25),
    (eq1_problema, "mat", "mat-conjuntos-funcoes", "mat-equacao-1grau", 30),
    (sistema_galinhas, "mat", "mat-conjuntos-funcoes", "mat-equacao-1grau", 15),
    (eq1_mmc, "mat", "mat-conjuntos-funcoes", "mat-equacao-1grau", 30),
    (eq1_ingressos, "mat", "mat-conjuntos-funcoes", "mat-equacao-1grau", 25),
    (eq1_multiplos, "mat", "mat-conjuntos-funcoes", "mat-equacao-1grau", 25),
    (eq1_fracionaria, "mat", "mat-conjuntos-funcoes", "mat-equacao-1grau", 25),
    (eq1_idades, "mat", "mat-conjuntos-funcoes", "mat-equacao-1grau", 25),
    (eq1_restante, "mat", "mat-conjuntos-funcoes", "mat-equacao-1grau", 25),
    (sistema_2x2, "mat", "mat-matrizes-sistemas", "mat-sistemas-lineares", 40),
    (ineq1_simples, "mat", "mat-conjuntos-funcoes", "mat-inequacoes", 50),
    (ineq1_inteiros, "mat", "mat-conjuntos-funcoes", "mat-inequacoes", 30),
    (ineq1_planos, "mat", "mat-conjuntos-funcoes", "mat-inequacoes", 25),
    (eq2_incompleta, "mat", "mat-conjuntos-funcoes", "mat-equacao-2grau", 30),
    (eq2_soma_produto, "mat", "mat-conjuntos-funcoes", "mat-equacao-2grau", 30),
    (eq2_area, "mat", "mat-conjuntos-funcoes", "mat-equacao-2grau", 25),
    (eq2_raizes, "mat", "mat-conjuntos-funcoes", "mat-equacao-2grau", 30),
    (delta, "mat", "mat-conjuntos-funcoes", "mat-equacao-2grau", 15),
    (afim_valor, "mat", "mat-conjuntos-funcoes", "mat-funcao-afim", 25),
    (afim_raiz, "mat", "mat-conjuntos-funcoes", "mat-funcao-afim", 20),
    (afim_dois_pontos, "mat", "mat-conjuntos-funcoes", "mat-funcao-afim", 20),
    (quad_raizes_grafico, "mat", "mat-conjuntos-funcoes", "mat-funcao-quadratica", 30),
    (quad_valor, "mat", "mat-conjuntos-funcoes", "mat-funcao-quadratica", 30),
    (quad_vertice, "mat", "mat-conjuntos-funcoes", "mat-funcao-quadratica", 25),
    (regra_tres_direta, "mat", "mat-aritmetica", "mat-razao-proporcao", 30),
    (regra_tres_inversa, "mat", "mat-aritmetica", "mat-razao-proporcao", 20),
    (porcentagem_de, "mat", "mat-porcentagem", "mat-porcentagem-basica", 30),
    (aumento_desconto, "mat", "mat-porcentagem", "mat-porcentagem-basica", 20),
    (juros, "mat", "mat-porcentagem", "mat-juros-compostos", 25),
    (mmc_problema, "mat", "mat-aritmetica", "mat-divisibilidade", 20),
    (mdc_problema, "mat", "mat-aritmetica", "mat-divisibilidade", 20),
    (potencias, "mat", "mat-log-exp", "mat-potencias-raizes", 25),
    (pa, "mat", "mat-sequencias", "mat-pa", 30),
    (pg, "mat", "mat-sequencias", "mat-pg", 20),
    (log_basico, "mat", "mat-log-exp", "mat-logaritmos", 25),
    (log_propriedades, "mat", "mat-log-exp", "mat-logaritmos", 20),
    (pitagoras, "mat", "mat-geometria-plana", "mat-triangulos", 25),
    (areas, "mat", "mat-geometria-plana", "mat-areas", 30),
    (volumes, "mat", "mat-geometria-espacial", None, 25),
    (probabilidade, "mat", "mat-probabilidade", "mat-prob-basica", 30),
    (media_mediana, "mat", "mat-estatistica", None, 30),
    (combinatoria, "mat", "mat-combinatoria", None, 25),
    (trig_notaveis, "mat", "mat-trigonometria", "mat-trig-triangulo", 20),
    (conversao, "mat", "mat-grandezas-medidas", "mat-conversao", 15),
    (mru, "fis", "fis-cinematica", "fis-mru", 30),
    (mruv, "fis", "fis-cinematica", "fis-muv", 30),
    (newton, "fis", "fis-dinamica", None, 30),
    (energia, "fis", "fis-energia", "fis-trabalho-energia", 30),
    (ohm, "fis", "fis-eletricidade", "fis-circuitos", 30),
    (consumo, "fis", "fis-eletricidade", "fis-potencia-consumo", 20),
    (densidade_pressao, "fis", "fis-hidrostatica", None, 25),
    (calor, "fis", "fis-termologia", "fis-calorimetria", 25),
    (ondas, "fis", "fis-ondulatoria", "fis-ondas", 20),
    (temperatura, "fis", "fis-termologia", "fis-termometria", 15),
]
SUB_BY_GEN = {"volumes": {"Uma caixa": "mat-prismas", "Um cilindro": "mat-cilindros"},
              "media_mediana": {"média": "mat-medias", "mediana": "mat-mediana-moda"},
              "combinatoria": {"Maria": "mat-pfc", "reunião": "mat-combinacao"},
              "newton": {"atrito": "fis-atrito-plano", "": "fis-leis-newton"},
              "densidade_pressao": {"densidade": "fis-empuxo", "pressão": "fis-pressao-stevin"}}


UGLY = re.compile(r"[+-] 0(?![\d,.])x?|(?<![\d.,])1x")


def main():
    out, seen = [], set()
    for fn, subject, topic, sub, count in GENERATORS:
        made, seed = 0, 0
        while made < count and seed < count * 6:
            q = fn(Builder(fn.__name__, subject, topic, sub, seed))
            seed += 1
            if q["stem"] in seen or len({o["t"] for o in q["opts"]}) < 5:
                continue  # repetida ou alternativas iguais: tenta outra semente
            if UGLY.search(q["stem"]):
                continue  # "+ 0", "+ 0x" ou "1x": ninguém escreve assim; tenta outra semente
            if not q["u"]:
                q["u"] = next(v for k, v in SUB_BY_GEN[fn.__name__].items() if k in q["stem"])
            seen.add(q["stem"])
            out.append(q)
            made += 1
    write_out("autoral", out)


if __name__ == "__main__":
    main()
