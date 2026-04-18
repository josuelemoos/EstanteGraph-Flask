"""Servicos para montagem do grafo de livros."""

from __future__ import annotations

from itertools import combinations

from sqlalchemy.orm import selectinload

from ..models import (
    Book,
    Connection,
    DEFAULT_NODE_COLOR,
    Genre,
    MANUAL_EDGE_COLOR,
    TAG_EDGE_COLOR,
    Tag,
)


def _node_size(rating: float | None) -> float:
    """Calcula o tamanho visual do no com base na nota."""

    if rating is None:
        return 7
    return 5 + (rating * 2)


def _node_payload(book: Book) -> dict:
    """Serializa um livro para o formato esperado pelo grafo."""

    first_genre = book.genres[0] if book.genres else None
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "status": book.status,
        "rating": book.rating,
        "color": first_genre.color_hex if first_genre else DEFAULT_NODE_COLOR,
        "size": _node_size(book.rating),
        "genres": [genre.name for genre in book.genres],
        "genre_ids": [genre.id for genre in book.genres],
        "tags": [tag.name for tag in book.tags],
    }


def _load_books(genre_id: int | None = None) -> list[Book]:
    """Carrega os livros com os relacionamentos usados pelo grafo."""

    query = Book.query.options(
        selectinload(Book.genres),
        selectinload(Book.tags),
    ).order_by(Book.id.asc())

    if genre_id is not None:
        query = query.join(Book.genres).filter(Genre.id == genre_id).distinct()

    return query.all()


def build_graph_payload(
    *,
    include_genre: bool = True,
    include_tag: bool = True,
    include_manual: bool = True,
    genre_id: int | None = None,
) -> dict:
    """Monta o payload completo de nos e arestas para o grafo."""

    books = _load_books(genre_id)
    if not books:
        return {"nodes": [], "edges": []}

    book_ids = [book.id for book in books]
    saved_connections = (
        Connection.query.filter(
            Connection.book_a_id.in_(book_ids),
            Connection.book_b_id.in_(book_ids),
        )
        .order_by(Connection.id.asc())
        .all()
    )

    manual_pairs = {(connection.book_a_id, connection.book_b_id) for connection in saved_connections}
    edges: list[dict] = []

    if include_manual:
        for connection in saved_connections:
            edges.append(
                {
                    "id": f"manual-{connection.id}",
                    "source": connection.book_a_id,
                    "target": connection.book_b_id,
                    "type": "manual",
                    "label": "conexao manual",
                    "note": connection.note,
                    "color": MANUAL_EDGE_COLOR,
                }
            )

    if include_genre:
        genre_groups: dict[int, dict] = {}
        for book in books:
            for genre in book.genres:
                group = genre_groups.setdefault(
                    genre.id,
                    {"genre": genre, "book_ids": []},
                )
                group["book_ids"].append(book.id)

        seen_pairs: set[tuple[int, int]] = set()
        for group in sorted(genre_groups.values(), key=lambda item: item["genre"].id):
            genre = group["genre"]
            unique_book_ids = sorted(set(group["book_ids"]))

            for source, target in combinations(unique_book_ids, 2):
                pair = (source, target)
                if pair in manual_pairs or pair in seen_pairs:
                    continue

                seen_pairs.add(pair)
                edges.append(
                    {
                        "id": f"genre-{source}-{target}",
                        "source": source,
                        "target": target,
                        "type": "genre",
                        "label": genre.name,
                        "color": genre.color_hex,
                    }
                )

    if include_tag:
        tag_groups: dict[int, dict] = {}
        for book in books:
            for tag in book.tags:
                group = tag_groups.setdefault(tag.id, {"tag": tag, "book_ids": []})
                group["book_ids"].append(book.id)

        seen_pairs: set[tuple[int, int]] = set()
        for group in sorted(tag_groups.values(), key=lambda item: item["tag"].id):
            tag: Tag = group["tag"]
            unique_book_ids = sorted(set(group["book_ids"]))

            for source, target in combinations(unique_book_ids, 2):
                pair = (source, target)
                if pair in manual_pairs or pair in seen_pairs:
                    continue

                seen_pairs.add(pair)
                edges.append(
                    {
                        "id": f"tag-{source}-{target}",
                        "source": source,
                        "target": target,
                        "type": "tag",
                        "label": tag.name,
                        "color": TAG_EDGE_COLOR,
                    }
                )

    return {
        "nodes": [_node_payload(book) for book in books],
        "edges": edges,
    }
