"""Blueprint com estatisticas gerais do dashboard."""

from __future__ import annotations

from flask import Blueprint
from sqlalchemy.orm import selectinload

from ..models import Book, Genre
from .graph_service import build_graph_payload
from .utils import success_response


stats_bp = Blueprint("stats", __name__)


@stats_bp.get("/stats")
def get_stats():
    """Retorna estatisticas agregadas para a dashboard."""

    books = Book.query.options(selectinload(Book.genres)).order_by(Book.id.asc()).all()
    rated_books = [book for book in books if book.rating is not None]
    graph_data = build_graph_payload()

    by_status = {status: 0 for status in ("want", "reading", "read")}
    for book in books:
        if book.status in by_status:
            by_status[book.status] += 1

    genres = Genre.query.options(selectinload(Genre.books)).order_by(Genre.name.asc()).all()
    by_genre = [
        {
            "genre": genre.name,
            "count": len(genre.books),
            "color_hex": genre.color_hex,
        }
        for genre in genres
    ]
    by_genre.sort(key=lambda item: (-item["count"], item["genre"].lower()))

    top_rated = (
        Book.query.filter(Book.rating.isnot(None))
        .order_by(Book.rating.desc(), Book.title.asc())
        .limit(5)
        .all()
    )

    payload = {
        "total": len(books),
        "by_status": by_status,
        "avg_rating": round(sum(book.rating for book in rated_books) / len(rated_books), 2) if rated_books else None,
        "total_connections": len(graph_data["edges"]),
        "by_genre": by_genre,
        "top_rated": [
            {
                "id": book.id,
                "title": book.title,
                "rating": book.rating,
            }
            for book in top_rated
        ],
    }
    return success_response(payload)
