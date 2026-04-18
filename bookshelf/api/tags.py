"""Blueprint com rotas de tags."""

from __future__ import annotations

from flask import Blueprint, request
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from ..models import Book, Tag, db
from .utils import error_response, normalize_text, success_response


tags_bp = Blueprint("tags", __name__)


@tags_bp.get("/tags")
def list_tags():
    """Lista todas as tags com contagem de livros."""

    tags = Tag.query.options(selectinload(Tag.books)).order_by(Tag.name.asc()).all()
    payload = []

    for tag in tags:
        item = tag.to_dict()
        item["book_count"] = len(tag.books)
        payload.append(item)

    return success_response(payload)


@tags_bp.post("/books/<int:book_id>/tags")
def add_tag_to_book(book_id: int):
    """Adiciona uma tag a um livro, criando-a se necessario."""

    book = Book.query.options(selectinload(Book.tags)).filter(Book.id == book_id).first()
    if book is None:
        return error_response("Livro nao encontrado", 404)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("body JSON invalido")

    name = normalize_text(payload.get("name"))
    if not name:
        return error_response("name e obrigatorio")

    tag = Tag.query.filter(func.lower(Tag.name) == name.lower()).first()
    if tag is None:
        tag = Tag(name=name)
        db.session.add(tag)
        db.session.flush()

    if any(existing_tag.id == tag.id for existing_tag in book.tags):
        return success_response(book.to_dict())

    book.tags.append(tag)
    db.session.commit()
    return success_response(book.to_dict(), 201)


@tags_bp.delete("/books/<int:book_id>/tags/<string:tag_name>")
def remove_tag_from_book(book_id: int, tag_name: str):
    """Remove uma tag de um livro sem apagar a tag global."""

    book = Book.query.options(selectinload(Book.tags)).filter(Book.id == book_id).first()
    if book is None:
        return error_response("Livro nao encontrado", 404)

    tag = Tag.query.filter(func.lower(Tag.name) == tag_name.lower()).first()
    if tag is None:
        return error_response("Tag nao encontrada", 404)

    if all(existing_tag.id != tag.id for existing_tag in book.tags):
        return error_response("Tag nao encontrada neste livro", 404)

    book.tags = [existing_tag for existing_tag in book.tags if existing_tag.id != tag.id]
    db.session.commit()
    return success_response(book.to_dict())
