# easyScieloPy (`easyscielopy`)

**easyScieloPy** é uma biblioteca Python para consulta, extração e parseamento programático e reprodutível de artigos e metadados da base científica [SciELO](https://scielo.org).

---

## Instalação

Instale o pacote básico via `pip`:

```bash
pip install easyscielopy
```

### Tabela de Extras de Instalação (D11)

O `easyscielopy` possui pacotes extras opcionais para habilitar funcionalidades específicas de análise, fontes externas e revisões sistemáticas:

| Extra | Dependências | O que habilita |
| :--- | :--- | :--- |
| `pandas` | `pandas` | Conversão e exportação direta de resultados para Pandas DataFrames (`to_dataframe`). |
| `openalex` | `pyalex` | Backend de busca e extração de metadados no acervo científico global OpenAlex (`source="openalex"`). |
| `review` | `rispy`, `bibtexparser`, `rapidfuzz`, `jinja2` | Pipeline completo de revisões sistemáticas (`easyscielo.review`), desduplicação fuzzy, importação/exportação RIS/BibTeX e relatórios PRISMA. |
| `screening` | `scikit-learn` | Ranqueamento automático por aprendizado de máquina / TF-IDF para auxílio na triagem de artigos. |
| `plots` | `matplotlib` | Geração visual de diagramas de fluxo PRISMA em formato de imagem (PNG). |
| `dev` | `pytest`, `ruff`, `mypy` | Ferramentas de desenvolvimento, análise estática e suíte de testes. |

Para instalar todos os recursos para revisões sistemáticas completas de uma só vez:

```bash
pip install "easyscielopy[pandas,openalex,review,screening,plots]"
```

---

## Backends e Fontes de Dados (Tabela D1)

O `easyscielopy` oferece uma arquitetura flexível com backends SciELO (`search`, `articlemeta`, `oai`) e integrações com fontes científicas externas (`openalex`, `crossref`). A escolha da fonte ou backend ideal depende da cobertura desejada (SciELO vs. literatura global) e das preferências de metadados e estabilidade.

### Tabela D1: Comparativo e Critérios de Escolha de Fontes e Backends

| Critério / Fonte | `search` | `articlemeta` | `oai` | `openalex` | `crossref` (Padrão) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Fonte / Cobertura** | Motor web SciELO (`search.scielo.org`) | API REST ArticleMeta SciELO | Provedor OAI-PMH SciELO | Acervo global OpenAlex (artigos, citações) | Registro global de DOIs Crossref |
| **Dependência** | Nenhuma | Nenhuma | Nenhuma | `pyalex` | Nenhuma |
| **Credencial** | Não exige | Não exige | Não exige | E-mail para Polite Pool (`OPENALEX_EMAIL`); Chave opcional (`OPENALEX_API_KEY`) | E-mail para Polite Pool (`CROSSREF_MAILTO`) |
| **Modo de Filtragem** | Busca textual completa no servidor | Filtragem local (client-side) | Coleta e filtragem local | API OpenAlex (busca textual, anos, ISSN) | API Crossref (busca bibliográfica, anos, ISSN) |
| **Estabilidade** | Média (raspagem HTML) | Alta (API REST oficial) | Altíssima (OAI-PMH) | Alta (API REST OpenAlex) | Alta (API REST Crossref) |
| **Quando Usar** | **Usar quando:** precisar de buscas textuais no motor oficial do SciELO. | **Usar quando:** necessitar de metadados completos em JSON da SciELO. | **Usar quando:** realizar coleta massiva via padrão Dublin Core. | **Usar quando:** buscar na literatura global além do SciELO com grafos de citação e tópicos. | **Usar quando:** buscar por DOI ou consultar registros oficiais de editoras globais. |
| **Estado (2026-09-07)** | **Bloqueado**: `search.scielo.org` responde HTTP 403 atrás do Bunny Shield (desafio JS). A biblioteca não contorna detecção de bot: a chamada levanta `BlockedError` com mensagem explícita. Volta a funcionar sozinha se a SciELO liberar. | **Saudável**, e é hoje o único caminho SciELO que responde. É um **harvester, não um motor de busca**: recorte por `collection` e `journal_issn` (medido: 3 artigos em ~7s com `scl` + ISSN `0102-311X`). Busca textual sem recorte varre o acervo inteiro (563.606 artigos só em `scl`) e não termina em tempo útil — a biblioteca avisa, mas não impede. | **Bloqueado**: mesmo shield em `www.scielo.br/oai/scielo-oai.php`. | Saudável. | Saudável. |

⚠️ **`crossref` é a fonte padrão desde 2026-09-07** (`iter_articles`/`search_articles`
e o `easyscielo search` da CLI, sem `--source`/`--backend`) porque a SciELO está
bloqueando requisição automatizada. `search_scielo()`/`iter_scielo()` (`api.py`)
continuam apontando para os backends SciELO (`backend="search"`) por padrão, de
propósito — são funções nomeadas para a SciELO, e trocar o default ali mentiria
no nome.

---

## Exemplos de Uso por Backend

### 1. Backend `search` (Raspagem do Motor de Busca — Padrão)

O backend `"search"` faz consultas diretas no mecanismo de busca web do SciELO, suportando filtros de coleção, idioma e intervalo de anos.

```python
from easyscielo import search_scielo, to_dataframe

# Busca de artigos usando o motor de busca do SciELO
articles = search_scielo(
    query="dengue",
    backend="search",
    collections=["bra", "col"],
    languages=["es", "pt"],
    year_start=2020,
    year_end=2023,
    n_max=20,
)

for art in articles:
    print(f"[{art.year}] {art.title} ({art.journal})")
    print(f"URL: {art.url}\n")

# Converter a lista de artigos para pandas DataFrame
df = to_dataframe(articles)
```

### 2. Backend `articlemeta` (API REST ArticleMeta)

O backend `"articlemeta"` consome a API REST oficial do SciELO ArticleMeta, realizando o parseamento dos registros JSON retornados.

```python
from easyscielo import iter_scielo

# Iterador para processar artigos via API ArticleMeta
for article in iter_scielo(
    query="epidemiology",
    backend="articlemeta",
    collections="bra",
    year_start=2021,
    n_max=50,
):
    print(f"DOI: {article.doi} | Título: {article.title}")
```

### 3. Backend `oai` (Provedor OAI-PMH)

O backend `"oai"` utiliza o protocolo padrão OAI-PMH da SciELO, retornando metadados no formato Dublin Core.

```python
from easyscielo import search_scielo, to_csv

# Coleta de artigos via protocolo OAI-PMH
articles = search_scielo(
    query="health",
    backend="oai",
    year_start=2019,
    year_end=2022,
    n_max=15,
)

# Exportar resultados diretamente para arquivo CSV
to_csv(articles, "resultados_oai.csv")
```

---

## Fontes Externas

Além dos backends próprios do SciELO, o `easyscielopy` permite consultar fontes científicas globais integradas (`openalex` e `crossref`) através das funções `search_articles` e `iter_articles`.

### Exemplo de Uso de Fontes Externas

```python
from easyscielo import search_articles, to_dataframe

# Busca combinada em fontes externas
articles = search_articles(
    query="dengue vaccine",
    sources=["openalex", "crossref"],
    year_start=2020,
    year_end=2023,
    n_max=20,
)

for art in articles:
    print(f"[{art.source}] {art.year} - {art.title} (DOI: {art.doi})")

# Converter a lista de artigos para pandas DataFrame
df = to_dataframe(articles)
```

### Configuração por Variáveis de Ambiente

Para obter respostas mais rápidas e limites mais generosos nas APIs públicas do OpenAlex e Crossref (*polite pool*), configure as variáveis de ambiente em seu sistema ou arquivo `.env`:

```bash
# E-mail de contato para o Polite Pool do OpenAlex (Recomendado)
export OPENALEX_EMAIL="seu-email@dominio.com"

# Chave de API opcional do OpenAlex (Apenas para contas Premium/API Key comercial)
export OPENALEX_API_KEY="sua_chave_opcional"

# E-mail de contato para o Polite Pool do Crossref (Recomendado)
export CROSSREF_MAILTO="seu-email@dominio.com"
```

> **Nota sobre credenciais do OpenAlex:** **A API pública do OpenAlex não exige chave** para funcionar. O que ela pede é apenas um e-mail de contato (`OPENALEX_EMAIL`) para direcionar suas requisições ao *polite pool*. A chave `OPENALEX_API_KEY` é totalmente opcional e necessária apenas para usuários de planos comerciais da plataforma.

---

## Systematic Review (`easyscielo.review`)

O submódulo `easyscielo.review` fornece um pipeline reprodutível para a condução de **Revisões Sistemáticas de Literatura**, alinhado ao fluxo **PRISMA 2020**. Ele abstrai as etapas de busca multi-fonte, desduplicação de registros, triagem por critérios e geração de relatórios.

### 1. Exemplo Mínimo de Ponta a Ponta

O fluxo básico consiste em definir um protocolo (`ReviewProtocol`), instanciar a classe `SystematicReview`, executar o pipeline através de `.run()` e consumir o relatório final:

```python
from easyscielo.review import (
    ReviewProtocol,
    ScreeningCriteria,
    SystematicReview,
)

# 1. Definir o protocolo da revisão (fontes, buscas e critérios de inclusão/exclusão)
protocol = ReviewProtocol(
    title="Revisão Sistemática sobre Vacinas contra Dengue",
    question="Qual a eficácia e segurança das vacinas contra dengue na América Latina?",
    queries=["dengue vaccine"],
    sources=["search", "openalex", "crossref"],
    query_filters={"year_start": 2020, "year_end": 2024},
    criteria=ScreeningCriteria(
        year_min=2020,
        required_terms=["dengue", "vaccine"],
        excluded_terms=["zika"],
    ),
)

# 2. Executar o pipeline de ponta a ponta (identificação -> desduplicação -> triagem -> relatório)
review = SystematicReview(protocol)
result = review.run()

# 3. Acessar o corpus resultante e o relatório PRISMA em Markdown
print(f"Total de registros identificados e triados: {len(result.corpus.records)}")
print(result.report)
```

### 2. Importação de Arquivos RIS / BibTeX de Outras Bases

É possível incorporar arquivos exportados em formato **RIS** ou **BibTeX** de outras bases de dados (como PubMed, Scopus ou Web of Science) ao mesmo corpus das buscas automatizadas SciELO + OpenAlex + Crossref:

```python
from easyscielo.review import (
    ReviewProtocol,
    ScreeningCriteria,
    SystematicReview,
    from_ris,
)

# Definir o protocolo multi-fonte
protocol = ReviewProtocol(
    title="Revisão Integrada SciELO + OpenAlex + Crossref + PubMed",
    queries=["dengue vector control"],
    sources=["search", "openalex", "crossref"],
    criteria=ScreeningCriteria(year_min=2020),
)

# Inicializar a revisão sistemática
review = SystematicReview(protocol)

# Importar registros de um arquivo RIS exportado do PubMed/Scopus
records_pubmed = from_ris("export_pubmed.ris", source_db="pubmed")

# Adicionar a nova fonte ao pipeline antes da desduplicação e triagem
review.add_source(records_pubmed)

# Executar a desduplicação e triagem unificada do corpus completo
result = review.run()

# Salvar o relatório PRISMA gerado
with open("relatorio_prisma.md", "w", encoding="utf-8") as f:
    f.write(result.report)
```

---

## Limitações Honestas

- **Backend `search` (Scraper HTML):**
  - O backend `search` continua sendo baseado em raspagem web (scraping HTML). Por isso, permanece suscetível a alterações imprevistas de layout no site do SciELO e a bloqueios temporários (HTTP 403 / rate limit) sob alto volume de consultas rápidas.
- **Triagem e Ranqueamento Automático (`easyscielo.review`):**
  - A triagem automática e o ranqueamento por relevância (TF-IDF) **priorizam a ordem de leitura** dos artigos mais promissores para o pesquisador, mas **não substituem o revisor humano**, que deve inspecionar e validar os critérios de inclusão/exclusão finais.
- **Backend `articlemeta` (API ArticleMeta):**
  - Realiza a filtragem dos critérios de busca **localmente (client-side)** após obter os registros da API, o que pode requerer maior transferência de dados dependendo da consulta.
- **Backend `oai` (OAI-PMH):**
  - Limitado pelo padrão **Dublin Core**, fornecendo um conjunto de metadados mais enxuto e simplificado do que a estrutura completa de artigos disponível nos demais backends.
- **Fontes Externas (`openalex` e `crossref`):**
  - **Teto Padrão de Registros:** Quando `n_max` não é especificado, as buscas em fontes externas possuem um teto default de **1.000 registros** por consulta.
  - **Filtros de Coleção SciELO:** Filtros específicos do ecossistema SciELO (como `collections`, `journals` e `categories`) não se aplicam fora do SciELO e são ignorados com emissão de aviso.
  - **Incompletude do Crossref:** O Crossref disponibiliza apenas o que a editora depositou, portanto o resumo (`abstract`) falta com frequência nos registros dessa fonte.

---

## Uso Responsável

Para evitar sobrecarga nos servidores do SciELO e garantir a continuidade das consultas:

- **Delays entre Requisições:** Utilize o parâmetro `delay` para incluir pausas aleatórias (em segundos) entre as requisições HTTP:
  ```python
  articles = search_scielo("zika", delay=(1.0, 3.0))
  ```
- **Cache Local:** Defina um diretório de cache com `cache_dir` para reaproveitar requisições de rede durante testes ou execuções iterativas:
  ```python
  articles = search_scielo("zika", cache_dir="./.cache_scielo")
  ```
- Respeite as políticas e termos de uso do ecossistema SciELO.

---

## Pacote Legado em R (`legacy-r/`)

A versão original do projeto desenvolvida em R foi preservada e está disponível no diretório [`legacy-r/`](legacy-r/). Consulte essa pasta para acessar o código original do pacote R e sua respectiva documentação.
