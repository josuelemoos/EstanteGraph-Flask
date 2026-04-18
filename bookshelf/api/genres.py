"""Blueprint com rotas de generos."""

from __future__ import annotations

from flask import Blueprint, request
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from ..models import Genre, db
from .utils import error_response, is_valid_hex_color, normalize_text, success_response


genres_bp = Blueprint("genres", __name__)


@genres_bp.get("/genres")
def list_genres():
    """Lista todos os generos com contagem de livros."""

    genres = Genre.query.options(selectinload(Genre.books)).order_by(Genre.name.asc()).all()
    payload = []

    for genre in genres:
        item = genre.to_dict()
        item["book_count"] = len(genre.books)
        payload.append(item)

    return success_response(payload)


@genres_bp.post("/genres")
def create_genre():
    """Cria um novo genero."""

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("body JSON invalido")

    name = normalize_text(payload.get("name"))
    color_hex = normalize_text(payload.get("color_hex")) or "#888780"

    if not name:
        return error_response("name e obrigatorio")

    if not is_valid_hex_color(color_hex):
        return error_response("color_hex deve estar no formato #RRGGBB")

    existing_genre = Genre.query.filter(func.lower(Genre.name) == name.lower()).first()
    if existing_genre is not None:
        return error_response("genero ja cadastrado")

    genre = Genre(name=name, color_hex=color_hex)
    db.session.add(genre)
    db.session.commit()
    return success_response(genre.to_dict(), 201)


@genres_bp.delete("/genres/<int:genre_id>")
def delete_genre(genre_id: int):
    """Remove um genero sem apagar os livros."""

    genre = db.session.get(Genre, genre_id)
    if genre is None:
        return error_response("Genero nao encontrado", 404)

    db.session.delete(genre)
    db.session.commit()
    return success_response({"deleted": True})
