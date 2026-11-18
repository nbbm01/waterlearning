# Fontes das questões

Tudo vem de bases abertas ou de provas publicadas pelos próprios órgãos. Nada foi raspado de site pago (QConcursos, TEC,
Estratégia): os termos desses sites proíbem coleta automatizada e os comentários dos professores têm dono.
Os números são do banco publicado, já sem repetidas, anuladas e questões que dependem de figura ausente.

## Questões reais

| Fonte | No banco | O que é | Licença | Importador |
|---|---:|---|---|---|
| [CEIA-POSITIVO/vestibular-gen_qa](https://huggingface.co/datasets/CEIA-POSITIVO/vestibular-gen_qa) | 14.787 | História e Geografia de ~200 vestibulares (UECE, UnB, UNESP, EsPCEx, ESA, AFA, EEAR, FUVEST, ENEM PPL…), com tags de assunto e dificuldade | não declarada | `vestibulares.py` |
| [openai/MMMLU](https://huggingface.co/datasets/openai/MMMLU) (PT_BR) | 13.030 | MMLU (UC Berkeley): questões de AP, GRE, USMLE e graduação, em tradução profissional | MIT | `mmlu.py` |
| [cabralski/MedQA-ptBR](https://huggingface.co/datasets/cabralski/MedQA-ptBR) | 11.740 | USMLE, o exame de licença médica dos EUA (MedQA), traduzido | não declarada (MedQA original: MIT) | `saude.py` |
| [li-lab/MMLU-ProX](https://huggingface.co/datasets/li-lab/MMLU-ProX) (pt) | 5.251 | Só as questões do MMLU-Pro que não vêm do MMLU: livros de STEM, TheoremQA, SciBench. De 10 alternativas ficam a certa e 4 sorteadas | MIT | `mmlu.py` |
| [Larxel/healthqa-br](https://huggingface.co/datasets/Larxel/healthqa-br) | 4.750 | Revalida e ENARE (residência médica e multiprofissional), financiado pelo Ministério da Saúde e CNPq | CC-BY-4.0 | `saude.py` |
| [russ7/oab_exams_2011_2025_combined](https://huggingface.co/datasets/russ7/oab_exams_2011_2025_combined) | 3.305 | OAB 1ª fase, 2010–2025 (inclui eduagarcia/oab_exams) | MIT | `oab.py` |
| [yunger7/enem-api](https://github.com/yunger7/enem-api) + [maritaca-ai/enem](https://huggingface.co/datasets/maritaca-ai/enem) | 2.859 | ENEM 2009–2024, todas as áreas, com imagens | MIT / Apache-2.0 | `enem.py`, `extras.py` |
| API das Questões | 2.115 | EsPCEx, militares, vestibulares e concursos (Banco do Brasil, Caixa, prefeituras, matérias de concurso); cresce todo dia | uso pela API com chave | `qdq_fetch.py`, `qdq.py` |
| [amalia-llm/pt_exams](https://huggingface.co/datasets/amalia-llm/pt_exams) | 1.744 | Exames Nacionais do secundário de Portugal | não declarada | `extras.py` |
| [BLUEX](https://github.com/portuguese-benchmark-datasets/BLUEX) | 1.106 | FUVEST e UNICAMP 2018–2024, todas as matérias | MIT | `bluex.py` |
| [northern-64bit/ENADE…MCQ_483](https://huggingface.co/datasets/northern-64bit/ENADE_Brazilian_national_university_examination_MCQ_483) | 411 | ENADE (INEP), vários cursos | não declarada (provas públicas do INEP) | `extras.py` |
| ITA (PDFs oficiais), FUVEST 2006–2017 (PDFs), livros FME e TAE | 2.375 | Recortes fiéis da página com o gabarito | provas públicas / livros do autor | `ita.py`, `fuvest.py`, `fme.py`, `tae.py` |
| [maritaca-ai/poscomp](https://huggingface.co/datasets/maritaca-ai/poscomp) | 127 | POSCOMP (SBC) | CC-BY-4.0 | `extras.py` |

"Não declarada" quer dizer que o dataset é público no Hugging Face, sem restrição de acesso, mas sem licença escrita.
As questões são de provas públicas. Se alguma fonte precisar sair, basta pôr o nome do arquivo em `SKIP_SOURCES`
(`pipeline/build.py`) e rodar `bun run data`.

## Questões geradas por computador (autorais)

1.664 (2,5% do banco): Matemática 1.259, Física 250 e Química 155. Existem só onde a prova real não chega, o degrau de
fixação ("quantos mols há em 36 g de água?"), que vestibular não cobra. Cada uma traz resolução passo a passo, as
alternativas erradas são erros típicos com o diagnóstico, e o gabarito é conferido por um caminho independente
(`audit_autoral.py`). Aparecem com a banca "Waterlearning".

## O que ficou de fora, e por quê

- **Fazzioni/concursos_2.3M, all_concursos_thinking, Vestibular_65k**: acesso fechado (aprovação manual) e sem origem
  declarada; os campos (órgão, cargo, slug) indicam raspagem de site de questões.
- **eliasjacob/agu_enem_oab_trf1**: só traz a resposta certa, sem as alternativas.
- **Global-MMLU, Portuguese-MMLU, Okapi**: as mesmas questões do MMLU em outra tradução.
- **MMLU moral_scenarios** (895): pares de cenários sobre "padrões morais dos EUA em 2020", não são questões de prova.
- **MedQA com figura** (960): o caso clínico cita uma imagem ("a fotomicrografia é mostrada") que o dataset não tem.
