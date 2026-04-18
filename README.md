# Bookshelf

Aplicação web em Flask para catalogar livros, acompanhar leituras e visualizar conexões em um grafo 3D.

## Requisitos

- Python 3.11+
- acesso à internet no navegador para carregar `three.js` e `3d-force-graph` via CDN

## Instalação

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

## Como rodar

1. Popular o banco com dados de teste:

```bash
.venv/bin/python seed.py
```

2. Iniciar a aplicação:

```bash
.venv/bin/flask --app app.py run
```

3. Abrir no navegador:

- `http://127.0.0.1:5000/` — dashboard da estante
- `http://127.0.0.1:5000/graph` — grafo 3D

## Fluxo de uso

- use o botão `+ livro` para criar livros
- filtre a estante por busca, status e gênero
- abra um livro para editar dados, mudar status e criar conexões manuais
- no grafo 3D, ligue e desligue arestas por tipo e filtre por gênero
- clique em um nó para voar a câmera até ele e abrir o painel lateral

## Estrutura principal

```text
bookshelf/
  api/          # blueprints REST
  templates/    # páginas Jinja2
  static/       # CSS e JavaScript
app.py          # ponto de entrada Flask
seed.py         # dados de teste
```

## API útil para desenvolvimento

- `GET /api/books`
- `GET /api/books/<id>`
- `GET /api/genres`
- `GET /api/stats`
- `GET /api/graph`

## Observações

- o banco padrão é SQLite em `bookshelf.db`
- o grafo 3D depende dos dados do `seed.py` para ficar visualmente interessante
- se quiser zerar o ambiente de teste, rode `seed.py` novamente
