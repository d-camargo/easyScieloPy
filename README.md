# easyScieloPy (`easyscielopy`)

**easyScieloPy** é uma biblioteca Python para consulta, extração e parseamento programático e reprodutível de artigos e metadados da base científica [SciELO](https://scielo.org).

---

## Instalação

Instale o pacote via `pip`:

```bash
pip install easyscielopy
```

Para suporte ao ecossistema Pandas (conversão direta de resultados para DataFrame):

```bash
pip install "easyscielopy[pandas]"
```

---

## Backends e Critério de Escolha (Tabela D1)

O `easyscielopy` oferece uma arquitetura flexível com **três backends** distintos para obtenção de dados. A escolha do backend ideal depende dos objetivos da sua pesquisa (precisão de busca textual em servidor vs. estabilidade e padrão de metadados).

### Tabela D1: Comparativo e Critérios de Escolha de Backends

| Critério / Backend | `search` (Padrão) | `articlemeta` | `oai` |
| :--- | :--- | :--- | :--- |
| **Fonte de Dados** | Motor de busca web SciELO (`search.scielo.org`) | API REST oficial do ArticleMeta SciELO | Provedor OAI-PMH (`scielo-oai.php`) |
| **Modo de Filtragem** | Busca textual completa (Full-text) no servidor | Filtragem local (client-side) de metadados | Coleta e filtragem local por conjuntos |
| **Riqueza de Metadados** | Estruturada completa (parseamento HTML) | JSON rico e detalhado de artigos | Padrão simplificado Dublin Core (XML) |
| **Estabilidade** | Média (suscetível a alterações de HTML) | Alta (API REST oficial de metadados) | Altíssima (padrão OAI-PMH internacional) |
| **Critério de Escolha** | **Usar quando:** precisar realizar buscas textuais avançadas e por palavras-chave no motor oficial da SciELO. | **Usar quando:** necessitar de metadados completos em JSON sem depender de raspagem HTML. | **Usar quando:** realizar coleta massiva, preservação digital e interoperação via padrão Dublin Core. |

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

## Limitações Honestas

- **Backend `search` (Scraper HTML):**
  - Suscetível a falhas ou quebras caso a estrutura HTML das páginas de resultado do SciELO seja alterada.
  - Sujeito a bloqueios temporários por limite de taxa de requisições (HTTP 403 / rate limit) ao enviar muitas consultas em sequência rápida.
- **Backend `articlemeta` (API ArticleMeta):**
  - Realiza a filtragem dos critérios de busca **localmente (client-side)** após obter os registros da API, o que pode requerer maior transferência de dados dependendo da consulta.
- **Backend `oai` (OAI-PMH):**
  - Limitado pelo padrão **Dublin Core**, fornecendo um conjunto de metadados mais enxuto e simplificado do que a estrutura completa de artigos disponível nos demais backends.

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
