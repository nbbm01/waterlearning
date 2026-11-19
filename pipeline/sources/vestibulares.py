"""Vestibulares de todo o país (História e Geografia) a partir do dataset aberto CEIA-POSITIVO/vestibular-gen_qa.

São ~15,7 mil questões reais de quase 600 provas (UECE, UnB, UNESP, EsPCEx, ESA, FUVEST, ENEM PPL...), já sem as
que dependem de imagem. Cada questão traz a prova de origem, a dificuldade e tags hierárquicas de assunto
("História do Brasil > República > Era Vargas"), que decidem o tópico antes das palavras-chave.
Baixe antes com hf_fetch.py.
"""
import ast
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, classify_topic, needs_figure, write_out

SRC = RAW / "hf" / "vestibular" / "train-00000-of-00001.jsonl"
SUBJECTS = {"História": "his", "Geografia": "geo"}
LEVEL = {"Fácil": 1, "Médio": 2, "Difícil": 3}

# nome da prova → banca: tira dia, fase, caderno, turno e curso ("UECE 2° Fase 2° Dia" → UECE)
RENAME = {"FGV-SP": "FGV", "FGV-RJ": "FGV", "Unit-SE": "Unit", "Unit-AL": "Unit", "FCMSCSP": "Santa Casa",
          "UEA-Específico": "UEA", "UNB": "UnB", "PUC-": "PUC", "PAS": "UFLA", "UEM/CVU": "UEM", "Atenas": "UniAtenas",
          "IFSulDeMinas": "IFSudMinas", "IFSul": "IFSudMinas", "Faculdade": "Faculdade Baiana de Direito",
          "Albert": "Albert Einstein", "São": "São Leopoldo Mandic", "Anhembi": "Anhembi Morumbi", "Santo": "Santo Agostinho",
          "Campo": "Campo Real", "IF": "IF Sertão", "IfSuldesteMinas": "IFSudesteMinas"}
# todas as PUCs ficam juntas, como no resto do banco
MERGE = {r"^PUC\b.*": "PUC"}


def exam_name(title):
    base = re.sub(r"\s*-\s*Quest[aã]o.*$", "", title)
    base = re.split(r"\s+(?:19|20)\d{2}", base)[0]
    base = re.sub(r"\([^)]*\)", "", base).strip()
    first = re.split(r"\s+", base)[0] if base else ""
    name = RENAME.get(first, first).rstrip("-")
    for pat, to in MERGE.items():
        if re.match(pat, name):
            name = to
    return name


# tags da fonte → tópico. As tags vêm do geral ao específico; vale a mais específica que tiver tópico.
HIS_TAGS = {
    "his-brasil-colonia": "Período Colonial (1530-1822)|Período Colonial|Sistema Colonial|Administração Colonial|Ciclos Econômicos Principais|"
                          "Ciclos Econômicos Secundários|Cana de Açúcar|Mineração|Período Pré-Colonial (1500 - 1530)|Bandeiras|Invasões Estrangeiras|"
                          "Holandeses|Nativistas|Emancipacionistas|Drogas do Sertão|Chegada dos Portugueses|Colônias de Exploração e Povoamento|"
                          "Processo de colonização|Escravidão",
    "his-brasil-imperio": "Império|Primeiro Reinado|Segundo Reinado|Período Regencial|Família Real Portuguesa no Brasil|Ciclo do Café",
    "his-republica-velha": "Primeira República (1889-1930)|República Oligárquica",
    "his-era-vargas": "Era Vargas (1930-1945)|Estado Novo",
    "his-brasil-contemporaneo": "República Democrática (1945-1964)|Governos Militares (1964-1985)|Nova República (1985 - ...)|Atos Institucionais|"
                                "Governo  Juscelino Kubitschek|Governo Goulart|Fernando Collor (90-92)|José Sarney (85-90)|Emílio Médici (69-74)|Populismo",
    "his-antiguidade": "Idade Antiga|Grécia|Roma|Egito|Mesopotâmia|Pré-História",
    "his-idade-media": "Idade Média|Feudalismo|Alta Idade Média|Baixa Idade Média|Cultura Medieval|Cruzadas|Império Bizantino|"
                       "Império Árabe/Mulçumano|Crise do Século XIV|Renascimento Urbano",
    "his-idade-moderna": "Idade Moderna|Absolutismo|Renascimento|Reformas religiosas e Contrarreforma|Expansão marítimo-comercial|Mercantilismo|"
                         "Revoluções Inglesas|Comercialista (Inglaterra)",
    "his-revolucoes-sec-xix": "Revolução Francesa|Era Napoleônica|Revolução Industrial (1ª Fase)|Revolução Industrial (2ª Fase)|"
                              "2ª Fase da Revolução Industrial|Neocolonialismo|Ideias sociais e políticas do século XIX|Iluminismo|"
                              "Revolução Americana (Independência)|Independência da América Latina|Partilha de territórios",
    "his-seculo-xx": "Primeira Guerra Mundial|1° Guerra Mundial|Segunda Guerra Mundial|Totalitarismo|Nazismo|Fascismo|Crise de 1929|Revolução Russa|"
                     "Guerra Fria|Descolonização Afro-asiática|Descolonização da África e Ásia|Nova Ordem Mundial|Pós-Segunda Guerra Mundial|URSS|"
                     "Ditaduras Latinas",
    "his-america": "América|Período pré-colombiano",
    "his-africa": "História da África|Africana",
    "his-teoria": "Fundamentos da História e historiografia|Fontes Históricas",
    "his-eua": "E.U.A.|Ações políticas e militares dos EUA",
}
GEO_TAGS = {
    "geo-conceitos": "Correntes do Pensamento Geográfico|Conceitos gerais|Conceitos Básicos|Espaço geográfico|Paisagem|Lugar|Região|"
                     "Geografia Critica (Marxista)|Quantitativa (Geografia Pragmática)|Cultural (Geografia Humanística)|Determinismo",
    "geo-cartografia": "Cartografia|Pontos de referência|Escala|Fuso Horário|Projeções Cartográficas|Mapa|Movimento da Terra e  Sistema Solar|"
                       "Estações do Ano|Cartografia - Geral",
    "geo-relevo": "Relevo|Geologia|Solos|Agente modeladores|Espaço Físico",
    "geo-clima": "Clima|Atmosfera|Clima - Geral",
    "geo-hidrografia": "Hidrografia|Recursos Hídricos",
    "geo-biomas": "Vegetação/Biomas|Biomas e ecossistemas brasileiros",
    "geo-ambiente": "Meio Ambiente|Impactos Ambientais|Políticas Ambientais|Biodiversidade/Preservação|Impactos da Ação Humana|Poluição do Ar|"
                    "Poluição da Água/Eutrofização|Química ambiental",
    "geo-populacao": "População|Sociedade  e População|Migrações|População - Brasil|Migrações - Brasil|Teorias Demográficas|População - Geral",
    "geo-urbanizacao": "Urbanização|Urbanização - Brasil",
    "geo-agraria": "Agricultura|Agronegócios|Pecuária|Extrativismo|Extrativismo - Brasil|Pesca|Agropecuária - Brasil",
    "geo-industria": "Indústria|Indústria - Brasil|Fontes de energia|Fontes de energia e recursos naturais|Energia - Brasil|Transportes|"
                     "Redes de transporte e de comunicação|Transportes/comunicações - Brasil|Comunicações",
    "geo-globalizacao": "Globalização|Blocos Econômicos|Comércio exterior e blocos econômicos|Comércio|Comércio - Brasil|Fluxos|Redes|"
                        "Modelos de Produção Capitalista|Tecnologias e Informação|Serviços|Trabalho|Capitalismo e Socialismo|Teorias Econômicas|"
                        "Pesquisa e desenvolvimento|Capitalismo",
    "geo-geopolitica": "Geopolitica|Conflitos|Oriente Médio|Bipolarização e Guerra Fria|Ações políticas e militares dos EUA|Primavera Árabe|"
                       "Estado Islâmico|Geopolítica - Brasil|Geopolítica - Geral|Guerra Fria",
    "geo-brasil": "Região Sul|Região Nordeste|Região Norte|Região Centro-Oeste|Região Sudeste|Regionalizações|Divisão Política Administrativa|Território",
    "geo-mundo": "Ásia|China|América|América do Sul|Europa|África|Estados Unidos|Japão|Índia|México|Sudeste Asiático|América Central|Rússia|"
                 "Canadá|Oceania|Antártida|CEI|Geografia regional",
}
# região do mundo só decide quando nenhuma tag temática decidiu
WEAK = {"geo-mundo", "his-america"}
TAG_TOPIC = {}
for table in (HIS_TAGS, GEO_TAGS):
    for topic, tags in table.items():
        for tag in tags.split("|"):
            TAG_TOPIC.setdefault((topic[:3], tag), topic)


def topic_from_tags(subj, tags):
    weak = None
    for tag in reversed(tags):
        topic = TAG_TOPIC.get((subj, tag))
        if topic and topic not in WEAK:
            return topic
        weak = weak or topic
    return weak


def clean(text):
    text = re.sub(r"[ \t ]+", " ", (text or "").replace("\r", ""))
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def main():
    out, skipped = [], collections.Counter()
    for line in open(SRC, encoding="utf-8"):
        row = json.loads(line)
        q = row["original_question"]
        subj = SUBJECTS.get(q["subject"])
        if not subj:
            continue
        alts = {k: clean(v) for k, v in (q["alternatives"] or {}).items() if v and clean(v)}
        # "Nenhuma das anteriores" foi acrescentada pelo dataset nas provas de 4 alternativas (3.625 casos, 3 delas gabarito)
        if alts.get("E") == "Nenhuma das anteriores" and q["answer"] != "E":
            del alts["E"]
        letters = [k for k in "ABCDE" if k in alts]
        stem = clean(q["question"])
        if q["answer"] not in letters or len(letters) < 4 or letters != list("ABCDE"[: len(letters)]):
            skipped["gabarito ou alternativas"] += 1
            continue
        if len(stem) < 25 or needs_figure(stem):
            skipped["depende de figura"] += 1
            continue
        if len({o.lower() for o in alts.values()}) < len(alts):
            skipped["alternativas repetidas"] += 1
            continue
        tags = ast.literal_eval(q["tags"]) if q["tags"] else []
        title = re.sub(r"\s*-\s*Quest[aã]o.*$", "", q["titulo"]).strip()
        year = re.search(r"(?:19|20)\d{2}", title)
        exam = exam_name(q["titulo"])
        topic = topic_from_tags(subj, tags) or classify_topic(stem + " " + " ".join(alts.values()), subj, " ".join(tags))
        out.append({
            "id": f"vest-{row['question_index']}", "s": subj, "e": exam or "Outras", "y": int(year.group()) if year else None,
            "t": topic, "d": LEVEL.get(q["dificuldade"], 2), "lvl": LEVEL.get(q["dificuldade"], 2), "k": "text",
            "stem": stem, "opts": [{"t": alts[k]} for k in letters], "ans": letters.index(q["answer"]),
            "tags": tags, "hint": " ".join(tags), "src": re.sub(r"\s+", " ", title),
        })
    print("descartadas:", dict(skipped))
    exams = collections.Counter(q["e"] for q in out)
    print(f"{len(exams)} bancas; maiores:", exams.most_common(25))
    write_out("vestibulares", out)


if __name__ == "__main__":
    main()
