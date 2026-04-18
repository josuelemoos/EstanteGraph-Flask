"""Rotas HTML da aplicação."""

from __future__ import annotations

from flask import Flask, render_template, request


def register_views(app: Flask) -> None:
    """Registra as páginas HTML da aplicação."""

    @app.get("/")
    def index() -> str:
        """Renderiza a dashboard principal da estante."""

        return render_template("index.html")

    @app.get("/graph")
    def graph() -> str:
        """Renderiza a página do grafo com placeholder da fase 3."""

        return render_template("graph.html", focus=request.args.get("focus"))

    @app.get("/books/<int:book_id>")
    def book_detail(book_id: int) -> str:
        """Renderiza a página de detalhe de um livro."""

        return render_template("book_detail.html", book_id=book_id)
