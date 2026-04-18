"""Modelos SQLAlchemy da aplicação."""

from __future__ import annotations

from datetime import datetime
import sqlite3

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, UniqueConstraint, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import relationship


db = SQLAlchemy()

ALLOWED_STATUS = {"want", "reading", "read"}
ALLOWED_CONNECTION_TYPES = {"manual", "genre", "tag"}
DEFAULT_NODE_COLOR = "#888780"
MANUAL_EDGE_COLOR = "#534AB7"
TAG_EDGE_COLOR = "#BA7517"


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    """Ativa chaves estrangeiras no SQLite para suportar cascata."""

    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


book_genres = db.Table(
    "book_genres",
    db.Column("book_id", db.Integer, db.ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    db.Column("genre_id", db.Integer, db.ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)

book_tags = db.Table(
    "book_tags",
    db.Column("book_id", db.Integer, db.ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Book(db.Model):
    """Livro catalogado na estante."""

    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    isbn = db.Column(db.String(20), nullable=True, unique=True)
    year = db.Column(db.Integer, nullable=True)
    cover_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="want")
    rating = db.Column(db.Float, nullable=True)
    review = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    genres = relationship("Genre", secondary=book_genres, back_populates="books", lazy="selectin")
    tags = relationship("Tag", secondary=book_tags, back_populates="books", lazy="selectin")
    connections_as_a = relationship(
        "Connection",
        foreign_keys="Connection.book_a_id",
        back_populates="book_a",
        lazy="selectin",
        passive_deletes=True,
    )
    connections_as_b = relationship(
        "Connection",
        foreign_keys="Connection.book_b_id",
        back_populates="book_b",
        lazy="selectin",
        passive_deletes=True,
    )

    def to_dict(self) -> dict:
        """Serializa o livro para JSON, incluindo gêneros e tags."""

        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "isbn": self.isbn,
            "year": self.year,
            "cover_url": self.cover_url,
            "status": self.status,
            "rating": self.rating,
            "review": self.review,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "genres": [genre.to_dict() for genre in self.genres],
            "tags": [tag.name for tag in self.tags],
        }

    def all_connections(self) -> list["Connection"]:
        """Retorna todas as conexões deste livro como origem ou destino."""

        return sorted(
            self.connections_as_a + self.connections_as_b,
            key=lambda connection: connection.id,
        )


class Genre(db.Model):
    """Gênero literário com cor própria para visualização."""

    __tablename__ = "genres"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    color_hex = db.Column(db.String(7), nullable=False, default=DEFAULT_NODE_COLOR)

    books = relationship("Book", secondary=book_genres, back_populates="genres", lazy="selectin")

    def to_dict(self) -> dict:
        """Serializa o gênero para JSON."""

        return {
            "id": self.id,
            "name": self.name,
            "color_hex": self.color_hex,
        }


class Tag(db.Model):
    """Rótulo livre para organização pessoal."""

    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    books = relationship("Book", secondary=book_tags, back_populates="tags", lazy="selectin")

    def to_dict(self) -> dict:
        """Serializa a tag para JSON."""

        return {"id": self.id, "name": self.name}


class Connection(db.Model):
    """Conexão entre dois livros."""

    __tablename__ = "connections"

    id = db.Column(db.Integer, primary_key=True)
    book_a_id = db.Column(db.Integer, db.ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    book_b_id = db.Column(db.Integer, db.ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    type = db.Column(db.String(20), nullable=False, default="manual")
    note = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    book_a = relationship("Book", foreign_keys=[book_a_id], back_populates="connections_as_a", lazy="joined")
    book_b = relationship("Book", foreign_keys=[book_b_id], back_populates="connections_as_b", lazy="joined")

    __table_args__ = (
        CheckConstraint("book_a_id < book_b_id", name="connection_order"),
        UniqueConstraint("book_a_id", "book_b_id", name="unique_connection"),
    )

    def to_dict(self) -> dict:
        """Serializa a conexão para JSON."""

        return {
            "id": self.id,
            "book_a": {"id": self.book_a.id, "title": self.book_a.title},
            "book_b": {"id": self.book_b.id, "title": self.book_b.title},
            "type": self.type,
            "note": self.note,
            "created_at": self.created_at.isoformat(),
        }
