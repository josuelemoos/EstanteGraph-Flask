"""Blueprint com rotas de CRUD de livros."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from flask import Blueprint, request
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from ..models import ALLOWED_STATUS, Book, Connection, Genre, Tag, db
from .utils import error_response, normalize_text, success_response


books_bp = Blueprint("books", __name__)

LIST_LOAD_OPTIONS = (
    selectinload(Book.genres),
    selectinload(Book.tags),
)

DETAIL_LOAD_OPTIONS = (
    selectinload(Book.genres),
    selectinload(Book.tags),
    selectinload(Book.connections_as_a).joinedload(Connection.book_b),
    selectinload(Book.connections_as_b).joinedload(Connection.book_a),
)

WIKIPEDIA_LANGUAGES = ("pt", "en")
WIKIPEDIA_HEADERS = {
    "User-Agent": "BookshelfApp/1.0 (https://example.local)"
}


def _parse_integer(value: Any, field_name: str) -> tuple[int | None, str | None]:
    """Converte um valor para inteiro quando presente."""

    if value in (None, ""):
        return None, None

    try:
        return int(value), None
    except (TypeError, ValueError):
        return None, f"{field_name} deve ser um inteiro"


def _parse_rating(value: Any) -> tuple[float | None, str | None]:
    """Converte e valida a nota do livro."""

    if value in (None, ""):
        return None, None

    try:
        rating = float(value)
    except (TypeError, ValueError):
        return None, "rating deve ser um numero"

    if not 1.0 <= rating <= 5.0:
        return None, "rating deve estar entre 1.0 e 5.0"

    return rating, None


def _normalize_unique_names(raw_values: Any, field_name: str) -> tuple[list[str] | None, str | None]:
    """Normaliza listas de strings preservando ordem e removendo duplicatas."""

    if raw_values is None:
        return [], None

    if not isinstance(raw_values, list):
        return None, f"{field_name} deve ser uma lista"

    normalized_names: list[str] = []
    seen_names: set[str] = set()

    for raw_name in raw_values:
        name = normalize_text(raw_name)
        if not name:
            return None, f"todos os itens de {field_name} devem ser strings nao vazias"
        if name.lower() in seen_names:
            continue
        seen_names.add(name.lower())
        normalized_names.append(name)

    return normalized_names, None


def _resolve_genres(genre_ids: Any) -> tuple[list[Genre] | None, str | None]:
    """Busca os generos informados no banco."""

    if genre_ids is None:
        return [], None

    if not isinstance(genre_ids, list):
        return None, "genre_ids deve ser uma lista"

    normalized_ids: list[int] = []
    seen_ids: set[int] = set()

    for raw_genre_id in genre_ids:
        parsed_id, error = _parse_integer(raw_genre_id, "genre_ids")
        if error:
            return None, "todos os itens de genre_ids devem ser inteiros"
        if parsed_id is None or parsed_id in seen_ids:
            continue
        seen_ids.add(parsed_id)
        normalized_ids.append(parsed_id)

    if not normalized_ids:
        return [], None

    genres = Genre.query.filter(Genre.id.in_(normalized_ids)).all()
    genre_map = {genre.id: genre for genre in genres}

    if len(genre_map) != len(normalized_ids):
        return None, "um ou mais generos nao foram encontrados"

    return [genre_map[genre_id] for genre_id in normalized_ids], None


def _resolve_tags(tag_names: Any) -> tuple[list[Tag] | None, str | None]:
    """Busca ou cria as tags informadas."""

    normalized_names, error = _normalize_unique_names(tag_names, "tags")
    if error:
        return None, error

    if not normalized_names:
        return [], None

    existing_tags = Tag.query.filter(Tag.name.in_(normalized_names)).all()
    tags_by_name = {tag.name: tag for tag in existing_tags}
    resolved_tags: list[Tag] = []

    for tag_name in normalized_names:
        tag = tags_by_name.get(tag_name)
        if tag is None:
            tag = Tag(name=tag_name)
            db.session.add(tag)
            db.session.flush()
            tags_by_name[tag_name] = tag
        resolved_tags.append(tag)

    return resolved_tags, None


def _book_detail_payload(book: Book) -> dict[str, Any]:
    """Monta a resposta detalhada de um livro com suas conexoes."""

    payload = book.to_dict()
    connections = []

    for connection in book.all_connections():
        other_book = connection.book_b if connection.book_a_id == book.id else connection.book_a
        connections.append(
            {
                "id": connection.id,
                "book": {
                    "id": other_book.id,
                    "title": other_book.title,
                },
                "type": connection.type,
                "note": connection.note,
            }
        )

    payload["connections"] = connections
    return payload


def _apply_book_payload(book: Book, payload: Any, *, partial: bool) -> str | None:
    """Valida e aplica os campos do payload em um livro."""

    if not isinstance(payload, dict):
        return "body JSON invalido"

    if not partial or "title" in payload:
        title = normalize_text(payload.get("title"))
        if not title:
            return "title e obrigatorio"
        book.title = title

    if not partial or "author" in payload:
        author = normalize_text(payload.get("author"))
        if not author:
            return "author e obrigatorio"
        book.author = author

    if "isbn" in payload:
        isbn = normalize_text(payload.get("isbn"))
        if isbn:
            existing_book = Book.query.filter(Book.isbn == isbn, Book.id != book.id).first()
            if existing_book:
                return "isbn ja cadastrado"
        book.isbn = isbn

    if "year" in payload:
        year, error = _parse_integer(payload.get("year"), "year")
        if error:
            return error
        book.year = year

    if "cover_url" in payload:
        book.cover_url = normalize_text(payload.get("cover_url"))

    if not partial or "status" in payload:
        status = normalize_text(payload.get("status")) or "want"
        if status not in ALLOWED_STATUS:
            return "status deve ser want, reading ou read"
        book.status = status

    if "rating" in payload:
        rating, error = _parse_rating(payload.get("rating"))
        if error:
            return error
        book.rating = rating

    if "review" in payload:
        book.review = normalize_text(payload.get("review"))

    if "genre_ids" in payload:
        genres, error = _resolve_genres(payload.get("genre_ids"))
        if error:
            return error
        book.genres = genres

    if "tags" in payload:
        tags, error = _resolve_tags(payload.get("tags"))
        if error:
            return error
        book.tags = tags

    return None


def _get_book_or_404(book_id: int) -> Book | None:
    """Busca um livro com os relacionamentos necessarios."""

    return (
        Book.query.options(*DETAIL_LOAD_OPTIONS)
        .filter(Book.id == book_id)
        .first()
    )


def _fetch_json(url: str) -> dict | list | None:
    """Busca um JSON remoto com timeout curto e falha silenciosa."""

    request_object = Request(url, headers=WIKIPEDIA_HEADERS)

    try:
        with urlopen(request_object, timeout=4) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def _search_wikipedia_page(search_term: str, language: str) -> str | None:
    """Busca o primeiro titulo de pagina para um termo na Wikipedia."""

    params = urlencode(
        {
            "action": "query",
            "list": "search",
            "srsearch": search_term,
            "utf8": 1,
            "format": "json",
            "srlimit": 1,
        }
    )
    payload = _fetch_json(f"https://{language}.wikipedia.org/w/api.php?{params}")

    if not isinstance(payload, dict):
        return None

    results = payload.get("query", {}).get("search", [])
    if not results:
        return None

    first_result = results[0]
    return normalize_text(first_result.get("title"))


def _fetch_wikipedia_summary_by_title(page_title: str, language: str) -> dict | None:
    """Busca o resumo de uma pagina da Wikipedia a partir do titulo."""

    payload = _fetch_json(
        f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{quote(page_title, safe='')}"
    )

    if not isinstance(payload, dict):
        return None

    extract = normalize_text(payload.get("extract"))
    summary_title = normalize_text(payload.get("title"))
    page_url = normalize_text(
        payload.get("content_urls", {})
        .get("desktop", {})
        .get("page")
    )

    if not extract or not summary_title:
        return None

    return {
        "title": summary_title,
        "extract": extract,
        "url": page_url,
        "language": language,
    }


def _fetch_wikipedia_summary(search_terms: list[str]) -> dict | None:
    """Busca um resumo relevante na Wikipedia tentando varios termos e idiomas."""

    normalized_terms = []
    seen_terms: set[str] = set()

    for raw_term in search_terms:
        term = normalize_text(raw_term)
        if not term:
            continue
        lowered = term.lower()
        if lowered in seen_terms:
            continue
        seen_terms.add(lowered)
        normalized_terms.append(term)

    for language in WIKIPEDIA_LANGUAGES:
        for term in normalized_terms:
            page_title = _search_wikipedia_page(term, language)
            if not page_title:
                continue

            summary = _fetch_wikipedia_summary_by_title(page_title, language)
            if summary:
                return summary

    return None


def _book_context_payload(book: Book) -> dict[str, Any]:
    """Monta o contexto externo do livro e do autor via Wikipedia."""

    book_summary = _fetch_wikipedia_summary(
        [
            f'{book.title} livro "{book.author}"',
            f"{book.title} livro",
            f"{book.title} romance",
            book.title,
        ]
    )
    author_summary = _fetch_wikipedia_summary(
        [
            f"{book.author} escritor",
            f"{book.author} author",
            book.author,
        ]
    )

    return {
        "book": book_summary,
        "author": author_summary,
    }


@books_bp.get("/books")
def list_books():
    """Lista livros com filtros e ordenacao opcionais."""

    query = Book.query.options(*LIST_LOAD_OPTIONS)

    search_term = normalize_text(request.args.get("q"))
    if search_term:
        pattern = f"%{search_term}%"
        query = query.filter(
            or_(
                Book.title.ilike(pattern),
                Book.author.ilike(pattern),
            )
        )

    status_filter = normalize_text(request.args.get("status"))
    if status_filter:
        if status_filter not in ALLOWED_STATUS:
            return error_response("status deve ser want, reading ou read")
        query = query.filter(Book.status == status_filter)

    genre_id = request.args.get("genre_id")
    if genre_id is not None:
        parsed_genre_id, error = _parse_integer(genre_id, "genre_id")
        if error:
            return error_response(error)
        query = query.join(Book.genres).filter(Genre.id == parsed_genre_id)

    tag_name = normalize_text(request.args.get("tag"))
    if tag_name:
        query = query.join(Book.tags).filter(Tag.name.ilike(tag_name))

    sort_field = (request.args.get("sort") or "created_at").strip().lower()
    order = (request.args.get("order") or "desc").strip().lower()

    sort_map = {
        "title": Book.title,
        "rating": Book.rating,
        "created_at": Book.created_at,
    }

    if sort_field not in sort_map:
        return error_response("sort deve ser title, rating ou created_at")

    if order not in {"asc", "desc"}:
        return error_response("order deve ser asc ou desc")

    sort_column = sort_map[sort_field]
    if order == "asc":
        query = query.order_by(sort_column.asc(), Book.id.asc())
    else:
        query = query.order_by(sort_column.desc(), Book.id.desc())

    books = query.distinct().all()
    return success_response([book.to_dict() for book in books])


@books_bp.post("/books")
def create_book():
    """Cria um novo livro."""

    payload = request.get_json(silent=True)
    book = Book()
    db.session.add(book)

    error = _apply_book_payload(book, payload, partial=False)
    if error:
        db.session.rollback()
        return error_response(error)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response("nao foi possivel criar o livro por conflito de dados")

    created_book = _get_book_or_404(book.id)
    return success_response(created_book.to_dict(), 201)


@books_bp.get("/books/<int:book_id>")
def get_book(book_id: int):
    """Retorna um livro com todos os dados e conexoes."""

    book = _get_book_or_404(book_id)
    if book is None:
        return error_response("Livro nao encontrado", 404)

    return success_response(_book_detail_payload(book))


@books_bp.get("/books/<int:book_id>/context")
def get_book_context(book_id: int):
    """Retorna contexto externo do livro e do autor."""

    book = db.session.get(Book, book_id)
    if book is None:
        return error_response("Livro nao encontrado", 404)

    return success_response(_book_context_payload(book))


@books_bp.put("/books/<int:book_id>")
def update_book(book_id: int):
    """Atualiza parcialmente um livro existente."""

    book = _get_book_or_404(book_id)
    if book is None:
        return error_response("Livro nao encontrado", 404)

    payload = request.get_json(silent=True)
    error = _apply_book_payload(book, payload, partial=True)
    if error:
        db.session.rollback()
        return error_response(error)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response("nao foi possivel atualizar o livro por conflito de dados")

    refreshed_book = _get_book_or_404(book_id)
    return success_response(refreshed_book.to_dict())


@books_bp.delete("/books/<int:book_id>")
def delete_book(book_id: int):
    """Remove um livro e suas conexoes."""

    book = _get_book_or_404(book_id)
    if book is None:
        return error_response("Livro nao encontrado", 404)

    for connection in book.all_connections():
        db.session.delete(connection)

    db.session.delete(book)
    db.session.commit()
    return success_response({"deleted": True})


@books_bp.put("/books/<int:book_id>/rating")
def update_book_rating(book_id: int):
    """Atualiza apenas a nota do livro."""

    book = db.session.get(Book, book_id)
    if book is None:
        return error_response("Livro nao encontrado", 404)

    payload = request.get_json(silent=True) or {}
    rating, error = _parse_rating(payload.get("rating"))
    if error:
        return error_response(error)
    if rating is None:
        return error_response("rating e obrigatorio")

    book.rating = rating
    db.session.commit()
    return success_response(book.to_dict())


@books_bp.put("/books/<int:book_id>/status")
def update_book_status(book_id: int):
    """Atualiza apenas o status de leitura."""

    book = db.session.get(Book, book_id)
    if book is None:
        return error_response("Livro nao encontrado", 404)

    payload = request.get_json(silent=True) or {}
    status = normalize_text(payload.get("status"))
    if status not in ALLOWED_STATUS:
        return error_response("status deve ser want, reading ou read")

    book.status = status
    db.session.commit()
    return success_response(book.to_dict())
