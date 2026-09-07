# GEMINI.md — easyscielopy

> **Este arquivo (`GEMINI.md`) é a fonte única das regras deste repo.**
> `CLAUDE.md` e `AGENTS.md` são symlinks relativos para cá. **Edite sempre
> o `GEMINI.md`** — o `agy` não segue symlink e só lê arquivo real, e o
> Edit do Claude Code recusa escrever através de symlink.

## O que é

O `easyscielopy` (`easyscielo`) é uma biblioteca Python para consulta, extração e parseamento programático e reprodutível de artigos e metadados da plataforma científica [SciELO](https://scielo.org). O projeto oferece suporte a três backends de busca e extração (`search`, `articlemeta` e `oai`), conversão simplificada de resultados para Pandas DataFrames, CSV ou dicionários, além de uma interface de linha de comando (CLI).

## Layout do Código (`src/easyscielo/`)

- `src/easyscielo/__init__.py`: Ponto de entrada e exportações da API pública.
- `src/easyscielo/api.py`: Funções principais de alto nível (`search_scielo`, `iter_scielo`).
- `src/easyscielo/models.py`: Dataclasses e estruturas de dados principais (`Article`, etc.).
- `src/easyscielo/http.py`: Gerenciamento de requisições HTTP, retries, timeouts e resiliência.
- `src/easyscielo/filters.py`: Validação e construção de filtros de busca (coleções, anos, idiomas, etc.).
- `src/easyscielo/frame.py`: Utilitários para conversão e exportação de dados (`to_dataframe`, `to_csv`).
- `src/easyscielo/cli.py`: Interface de linha de comando (`easyscielo`).
- `src/easyscielo/errors.py`: Hierarquia de exceções personalizadas (`ScieloError`, etc.).
- `src/easyscielo/backends/`: Módulos de suporte e integração com os backends da SciELO:
  - `search_html.py`: Backend de busca web e raspagem/parser HTML.
  - `articlemeta.py`: Backend para consumo da API REST oficial ArticleMeta (JSON).
  - `oai.py`: Backend para consumo do provedor OAI-PMH (XML Dublin Core).

## Regras de Trabalho e Testes

- **Fixtures para Parsers**: Todo parser novo ou alteração em parser existente entra obrigatoriamente com fixture gravada em `tests/fixtures/`.
- **Isolamento de Rede por Padrão**: Nenhum teste automatizado do projeto bate na rede por padrão. Todos os testes devem rodar offline utilizando mocks ou as fixtures previamente salvas.

## Regravação de Fixtures

Para atualizar ou capturar novas fixtures reais de HTML/JSON/XML a partir dos servidores da SciELO, execute o script:

```bash
python tools/capture_fixtures.py
```

Esse script faz as chamadas HTTP necessárias e salva os arquivos diretamente em `tests/fixtures/`. Caso a rede esteja inacessível ou ocorra falha de conexão, o script gera automaticamente fallbacks válidos para garantir a consistência das fixtures.
