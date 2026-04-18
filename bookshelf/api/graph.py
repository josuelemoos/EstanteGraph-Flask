"""Blueprint do endpoint de grafo."""

from __future__ import annotations

from flask import Blueprint, request

from .graph_service import build_graph_payload
from .utils import error_response, parse_bool, success_response


graph_bp = Blueprint("graph", __name__)


@graph_bp.get("/graph")
def get_graph():
    """Retorna o grafo completo de livros e conexoes."""

    raw_genre_id = request.args.get("genre_id")
    genre_id = None

    if raw_genre_id not in (None, ""):
        try:
            genre_id = int(raw_genre_id)
        except (TypeError, ValueError):
            return error_response("genre_id deve ser um inteiro")

    payload = build_graph_payload(
        include_genre=parse_bool(request.args.get("include_genre"), True),
        include_tag=parse_bool(request.args.get("include_tag"), True),
        include_manual=parse_bool(request.args.get("include_manual"), True),
        genre_id=genre_id,
    )
    return success_response(payload)
