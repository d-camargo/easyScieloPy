# GEMINI.md — easyscielopy

> **Este arquivo (`GEMINI.md`) é a fonte única das regras deste repo.**
> `CLAUDE.md` e `AGENTS.md` são symlinks relativos para cá. **Edite sempre
> o `GEMINI.md`** — o `agy` não segue symlink e só lê arquivo real, e o
> Edit do Claude Code recusa escrever através de symlink.

## O que é

O `easyscielopy` (`easyscielo`) é uma biblioteca Python para consulta, extração e parseamento programático e reprodutível de artigos e metadados da plataforma científica [SciELO](https://scielo.org). O projeto oferece suporte a três backends de busca e extração (`search`, `articlemeta` e `oai`), conversão simplificada de resultados para Pandas DataFrames, CSV ou dicionários, além de uma interface de linha de comando (CLI).

## Quem consome esta biblioteca

O **sci-team** (`~/projects/sci-team`, canal `#sci-team`) usa o subpacote `review/` como motor de revisão sistemática, chamando **`/home/diego/projects/easyscielopy/.venv/bin/easyscielo review run --protocol <p.json> --out-dir <dir>` por subprocess** — nunca `import easyscielo`. Ele depende dos 5 arquivos que esse comando grava no `--out-dir` (`corpus.csv`, `included.ris`, `prisma.json`, `report.md`, `provenance.json`) e dos nomes das chaves do `prisma.json`. **Mudar esses nomes quebra o sci-team em silêncio** — se mudar, mude junto `src/revisao.py` lá. A divisão de papéis (aqui é busca e revisão; a base de citação é o Zotero, do lado de lá) está na D28 do `GEMINI.md` do sci-team e em `~/.hermes/MAPA.md` §7.

## Layout do Código (`src/easyscielo/`)

- `src/easyscielo/__init__.py`: Ponto de entrada e exportações da API pública.
- `src/easyscielo/api.py`: Funções principais de alto nível (`search_scielo`, `iter_scielo`).
- `src/easyscielo/models.py`: Dataclasses e estruturas de dados principais (`Article`, etc.).
- `src/easyscielo/http.py`: Gerenciamento de requisições HTTP, retries, timeouts e resiliência.
- `src/easyscielo/filters.py`: Validação e construção de filtros de busca (coleções, anos, idiomas, etc.).
- `src/easyscielo/frame.py`: Utilitários para conversão e exportação de dados (`to_dataframe`, `to_csv`).
- `src/easyscielo/cli.py`: Interface de linha de comando (`easyscielo`).
- `src/easyscielo/errors.py`: Hierarquia de exceções personalizadas (`ScieloError`, etc.).
- `src/easyscielo/_optional.py`: Importação de dependências opcionais com mensagem de instalação do extra correspondente (`require`).
- `src/easyscielo/config.py`: Resolução de credenciais e contatos das APIs externas (argumento explícito → variável de ambiente → `None`).
- `src/easyscielo/sources.py`: Iteração e materialização de resultados de múltiplas fontes (`iter_articles`, `SCIELO_SOURCES`, `EXTERNAL_SOURCES`).
- `src/easyscielo/backends/`: Módulos de suporte e integração com os backends de busca e metadados:
  - `search_html.py`: Backend de busca web e raspagem/parser HTML.
  - `articlemeta.py`: Backend para consumo da API REST oficial ArticleMeta (JSON).
  - `oai.py`: Backend para consumo do provedor OAI-PMH (XML Dublin Core).
  - `openalex.py`: Backend para consumo da API OpenAlex (JSON).
  - `crossref.py`: Backend para consumo da API Crossref (JSON).
- `src/easyscielo/review/`: Subpacote de revisão sistemática (PRISMA 2020):
  - `models.py`: Estruturas do corpus de revisão (`ReviewRecord`, `Corpus`, `Stage`, `Decision`, `make_record_id`).
  - `normalize.py`: Normalização de DOI, título e autor e chave de blocagem para comparação (`blocking_key`).
  - `dedup.py`: Deduplicação de registros entre fontes com resultado auditável (`deduplicate`, `DedupResult`).
  - `importers.py`: Importação de registros externos em RIS, BibTeX e CSV (`from_ris`, `from_bibtex`, `from_csv`, `from_articles`).
  - `exporters.py`: Exportação do corpus em RIS, BibTeX, CSV e JSON (`to_ris`, `to_bibtex`, `to_review_csv`, `to_json`).
  - `screening.py`: Triagem determinística e auditável e ordenação por relevância (`ScreeningCriteria`, `screen`, `rank_by_relevance`).
  - `metrics.py`: Métricas de avaliação e comparação de estratégias de busca (`evaluate_strategy`, `compare_strategies`, `coverage_by_*`).
  - `prisma.py`: Contagens do fluxo PRISMA e geração do diagrama (`prisma_counts`, `to_mermaid`, `to_png`).
  - `protocol.py`: Protocolo da revisão, serialização e proveniência reprodutível (`ReviewProtocol`, `provenance`, `compute_corpus_sha256`).
  - `pipeline.py`: Orquestração ponta a ponta da revisão (`SystematicReview`, `ReviewResult`).
  - `report.py`: Renderização do relatório final via Jinja2 (`render_report`).
  - `templates/`: Templates Jinja2 do relatório (`report.md.j2`, `report.html.j2`).

## Regras de Trabalho e Testes

- **Fixtures para Parsers**: Todo parser novo ou alteração em parser existente entra obrigatoriamente com fixture gravada em `tests/fixtures/`.
- **Isolamento de Rede por Padrão**: Nenhum teste automatizado do projeto bate na rede por padrão. Todos os testes devem rodar offline utilizando mocks ou as fixtures previamente salvas.
- **Fonte Nova é Backend**: Toda fonte nova implementa o `Backend` Protocol e entra no registro de backends. Não se cria abstração paralela para acomodar uma fonte.
- **Credencial só por Variável de Ambiente**: Chaves de API e e-mails de contato vêm exclusivamente de variáveis de ambiente (ou de argumento explícito de quem chama), nunca de arquivo versionado. Nenhum teste depende de credencial nem de rede.
- **Dependência de Revisão é Sempre Extra**: Toda dependência do subpacote `review/` (`rispy`, `bibtexparser`, `rapidfuzz`, `jinja2`, `scikit-learn`, `matplotlib`, etc.) entra em `[project.optional-dependencies]` como extra e é importada preguiçosamente dentro da função, via `_optional.require`. Nunca em `dependencies`, nunca com `import` no topo do módulo: instalar o `easyscielo` sem os extras tem que continuar funcionando, e importar `easyscielo.review` não pode quebrar por falta de extra.

## Regravação de Fixtures

Para atualizar ou capturar novas fixtures reais de HTML/JSON/XML a partir dos servidores da SciELO, execute o script:

```bash
python tools/capture_fixtures.py
```

Esse script faz as chamadas HTTP necessárias e salva os arquivos diretamente em `tests/fixtures/`. Caso a rede esteja inacessível ou ocorra falha de conexão, o script gera automaticamente fallbacks válidos para garantir a consistência das fixtures.
