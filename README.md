# Bookshelf

Bookshelf é uma aplicação web para organizar livros, acompanhar leitura e explorar relações entre obras em uma visualização de grafo 3D.

## O que o site faz

Com o Bookshelf você pode:

- cadastrar livros com título, autor, ano, status, nota, tags, gêneros e resenha
- filtrar a estante por busca, status de leitura e gênero
- abrir a página de cada livro para editar dados e criar conexões manuais
- visualizar estatísticas gerais da coleção
- navegar por um grafo 3D com relações por gênero, tag e conexões manuais
- clicar em um nó do grafo para abrir um painel com mais contexto do livro

## Como o Flask foi utilizado

O projeto usa Flask como camada principal da aplicação:

- `app.py` cria a aplicação com factory pattern
- `bookshelf/api/` concentra os blueprints REST, responsáveis por CRUD, stats, conexões e grafo
- `bookshelf/templates/` renderiza as páginas HTML com Jinja2
- `bookshelf/static/` guarda CSS e JavaScript usados no frontend
- `Flask-SQLAlchemy` faz a integração entre Flask e SQLite para persistência dos dados
- `Flask-CORS` deixa os endpoints preparados para consumo no frontend quando necessário

Na prática, o Flask organiza o projeto em duas frentes:

1. páginas HTML server-side, como dashboard, detalhe do livro e grafo
2. API JSON para livros, gêneros, tags, conexões, estatísticas e dados do grafo

### Funções e recursos do Flask usados no projeto

As partes principais do Flask usadas aqui são:

- `Flask(__name__)` para criar a aplicação principal
- `create_app()` para organizar a configuração no formato factory pattern
- `@app.get(...)` para registrar as rotas HTML
- `Blueprint(...)` para separar os endpoints da API por responsabilidade
- `@books_bp.get(...)`, `@books_bp.post(...)`, `@books_bp.put(...)` e `@books_bp.delete(...)` para declarar rotas REST
- `render_template(...)` para renderizar páginas com Jinja2
- `request` para ler query params e payload JSON enviados pelo cliente
- `jsonify(...)` para devolver respostas JSON padronizadas
- `url_for(...)` nos templates para referenciar arquivos estáticos com segurança
- `app.app_context()` para inicializar o banco e executar operações ligadas ao contexto da aplicação

## Tecnologias

- Python 3.11+
- Flask
- Flask-SQLAlchemy
- SQLite
- Jinja2
- JavaScript vanilla
- Three.js + 3d-force-graph via CDN

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

2. Subir a aplicação:

```bash
.venv/bin/flask --app app.py run
```

3. Abrir no navegador:

- `http://127.0.0.1:5000/` — estante e dashboard
- `http://127.0.0.1:5000/graph` — grafo 3D

## Estrutura principal

```text
bookshelf/
  api/          # blueprints REST
  templates/    # páginas HTML com Jinja2
  static/       # CSS e JavaScript do frontend
app.py          # ponto de entrada da aplicação
seed.py         # dados iniciais para teste
requirements.txt
```

## Endpoints úteis

- `GET /api/books`
- `GET /api/books/<id>`
- `GET /api/books/<id>/context`
- `GET /api/genres`
- `GET /api/stats`
- `GET /api/graph`

## Observações

- o banco padrão é SQLite e fica em `bookshelf.db`
- o grafo 3D depende de dados suficientes para ficar interessante, por isso a `seed.py` ajuda bastante
- o navegador precisa conseguir carregar `three.js` e `3d-force-graph` via internet
