"""Blueprint com rotas de conexoes entre livros."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, request
from sqlalchemy import or_

from ..models import Book, Connection, db
from .utils import error_response, normalize_text, success_response


connections_bp = Blueprint("connections", __name__)


def _normalize_connection_pair(book_a_id: int, book_b_id: int) -> tuple[int, int]:
    """Ordena o par de livros para respeitar a constraint do banco."""

    if book_a_id < book_b_id:
        return book_a_id, book_b_id
    return book_b_id, book_a_id


def _parse_book_id(value: Any, field_name: str) -> tuple[int | None, str | None]:
    """Converte um identificador para inteiro."""

    try:
        return int(value), None
    except (TypeError, ValueError):
        return None, f"{field_name} deve ser um inteiro"


@connections_bp.get("/connections")
def list_connections():
    """Lista todas as conexoes cadastradas."""

    connections = Connection.query.order_by(Connection.created_at.desc(), Connection.id.desc()).all()
    return success_response([connection.to_dict() for connection in connections])


@connections_bp.post("/connections")
def create_connection():
    """Cria uma conexao manual entre dois livros."""

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("body JSON invalido")

    book_a_id, error = _parse_book_id(payload.get("book_a_id"), "book_a_id")
    if error:
        return error_response(error)

    book_b_id, error = _parse_book_id(payload.get("book_b_id"), "book_b_id")
    if error:
        return error_response(error)

    if book_a_id == book_b_id:
        return error_response("book_a_id e book_b_id devem ser diferentes")

    book_a_id, book_b_id = _normalize_connection_pair(book_a_id, book_b_id)

    book_a = db.session.get(Book, book_a_id)
    book_b = db.session.get(Book, book_b_id)
    if book_a is None or book_b is None:
        return error_response("um ou ambos os livros nao foram encontrados", 404)

    existing_connection = Connection.query.filter_by(book_a_id=book_a_id, book_b_id=book_b_id).first()
    if existing_connection is not None:
        return error_response("conexao ja existente")

    connection_type = normalize_text(payload.get("type")) or "manual"
    if connection_type != "manual":
        return error_response("type deve ser manual")

    connection = Connection(
        book_a_id=book_a_id,
        book_b_id=book_b_id,
        type=connection_type,
        note=normalize_text(payload.get("note")),
    )
    db.session.add(connection)
    db.session.commit()
    return success_response(connection.to_dict(), 201)


@connections_bp.delete("/connections/<int:connection_id>")
def delete_connection(connection_id: int):
    """Remove uma conexao existente."""

    connection = db.session.get(Connection, connection_id)
    if connection is None:
        return error_response("Conexao nao encontrada", 404)

    db.session.delete(connection)
    db.session.commit()
    return success_response({"deleted": True})


@connections_bp.get("/books/<int:book_id>/connections")
def list_book_connections(book_id: int):
    """Lista todas as conexoes ligadas a um livro especifico."""

    book = db.session.get(Book, book_id)
    if book is None:
        return error_response("Livro nao encontrado", 404)

    connections = (
        Connection.query.filter(
            or_(
                Connection.book_a_id == book_id,
                Connection.book_b_id == book_id,
            )
        )
        .order_by(Connection.created_at.desc(), Connection.id.desc())
        .all()
    )
    return success_response([connection.to_dict() for connection in connections])
