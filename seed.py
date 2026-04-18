"""Popula o banco com dados de teste para a aplicação."""

from __future__ import annotations

from bookshelf import create_app
from bookshelf.models import Book, Connection, Genre, Tag, db


GENRES_DATA = [
    {"name": "sci-fi", "color_hex": "#378ADD"},
    {"name": "distopia", "color_hex": "#D85A30"},
    {"name": "clássico", "color_hex": "#1D9E75"},
    {"name": "não-ficção", "color_hex": "#639922"},
    {"name": "fantasia", "color_hex": "#7F77DD"},
    {"name": "filosofia", "color_hex": "#BA7517"},
    {"name": "história", "color_hex": "#D4537E"},
    {"name": "thriller", "color_hex": "#888780"},
]

BOOKS_DATA = [
    {"title": "Duna", "author": "Frank Herbert", "year": 1965, "status": "read", "rating": 5.0, "genres": ["sci-fi", "fantasia"], "tags": ["favorito", "clássico"]},
    {"title": "Fundação", "author": "Isaac Asimov", "year": 1951, "status": "read", "rating": 4.8, "genres": ["sci-fi"], "tags": ["clássico"]},
    {"title": "Neuromancer", "author": "William Gibson", "year": 1984, "status": "read", "rating": 4.2, "genres": ["sci-fi"], "tags": []},
    {"title": "A Mão Esquerda da Escuridão", "author": "Ursula K. Le Guin", "year": 1969, "status": "want", "rating": None, "genres": ["sci-fi"], "tags": []},
    {"title": "Solaris", "author": "Stanisław Lem", "year": 1961, "status": "reading", "rating": None, "genres": ["sci-fi"], "tags": ["difícil"]},
    {"title": "1984", "author": "George Orwell", "year": 1949, "status": "read", "rating": 4.5, "genres": ["distopia", "clássico"], "tags": ["favorito"]},
    {"title": "Admirável Mundo Novo", "author": "Aldous Huxley", "year": 1932, "status": "read", "rating": 4.3, "genres": ["distopia", "sci-fi"], "tags": []},
    {"title": "Fahrenheit 451", "author": "Ray Bradbury", "year": 1953, "status": "want", "rating": None, "genres": ["distopia"], "tags": []},
    {"title": "O Senhor dos Anéis", "author": "J.R.R. Tolkien", "year": 1954, "status": "read", "rating": 5.0, "genres": ["fantasia"], "tags": ["favorito", "releitura"]},
    {"title": "As Crônicas de Nárnia", "author": "C.S. Lewis", "year": 1950, "status": "read", "rating": 4.0, "genres": ["fantasia"], "tags": []},
    {"title": "Sapiens", "author": "Yuval Noah Harari", "year": 2011, "status": "read", "rating": 4.4, "genres": ["não-ficção", "história"], "tags": ["favorito"]},
    {"title": "O Gene", "author": "Siddhartha Mukherjee", "year": 2016, "status": "reading", "rating": None, "genres": ["não-ficção"], "tags": ["ciência"]},
    {"title": "Cosmos", "author": "Carl Sagan", "year": 1980, "status": "read", "rating": 4.9, "genres": ["não-ficção", "sci-fi"], "tags": ["favorito", "clássico"]},
    {"title": "O Mundo de Sofia", "author": "Jostein Gaarder", "year": 1991, "status": "read", "rating": 4.1, "genres": ["filosofia"], "tags": []},
    {"title": "Assim Falou Zaratustra", "author": "Friedrich Nietzsche", "year": 1883, "status": "want", "rating": None, "genres": ["filosofia", "clássico"], "tags": ["difícil"]},
    {"title": "Dom Casmurro", "author": "Machado de Assis", "year": 1899, "status": "read", "rating": 4.7, "genres": ["clássico"], "tags": ["brasil"]},
    {"title": "O Processo", "author": "Franz Kafka", "year": 1925, "status": "read", "rating": 4.3, "genres": ["clássico", "filosofia"], "tags": ["existencial"]},
    {"title": "Cem Anos de Solidão", "author": "Gabriel García Márquez", "year": 1967, "status": "reading", "rating": None, "genres": ["clássico", "fantasia"], "tags": []},
    {"title": "O Silêncio dos Inocentes", "author": "Thomas Harris", "year": 1988, "status": "read", "rating": 4.5, "genres": ["thriller"], "tags": []},
    {"title": "Garota Exemplar", "author": "Gillian Flynn", "year": 2012, "status": "want", "rating": None, "genres": ["thriller"], "tags": []},
]

MANUAL_CONNECTIONS_DATA = [
    {"book_a": "Duna", "book_b": "1984", "note": "ambos exploram controle político e propaganda"},
    {"book_a": "Fundação", "book_b": "Sapiens", "note": "ambos tentam prever o futuro da civilização"},
    {"book_a": "Solaris", "book_b": "Cosmos", "note": "exploração do desconhecido e limites do conhecimento humano"},
    {"book_a": "O Senhor dos Anéis", "book_b": "Assim Falou Zaratustra", "note": "a jornada de transformação do protagonista"},
    {"book_a": "O Processo", "book_b": "O Mundo de Sofia", "note": "absurdo e busca por sentido"},
    {"book_a": "Admirável Mundo Novo", "book_b": "Assim Falou Zaratustra", "note": "questões sobre liberdade e superar a humanidade"},
]


def seed() -> None:
    """Popula o banco com dados iniciais consistentes para testes."""

    app = create_app()

    with app.app_context():
        db.session.query(Connection).delete()
        db.session.execute(db.delete(Book.tags.property.secondary))
        db.session.execute(db.delete(Book.genres.property.secondary))
        db.session.query(Book).delete()
        db.session.query(Genre).delete()
        db.session.query(Tag).delete()
        db.session.commit()

        genre_map: dict[str, Genre] = {}
        for genre_data in GENRES_DATA:
            genre = Genre(**genre_data)
            db.session.add(genre)
            db.session.flush()
            genre_map[genre_data["name"]] = genre

        tag_map: dict[str, Tag] = {}
        book_map: dict[str, Book] = {}

        for book_data in BOOKS_DATA:
            book = Book(
                title=book_data["title"],
                author=book_data["author"],
                year=book_data.get("year"),
                status=book_data["status"],
                rating=book_data.get("rating"),
            )
            db.session.add(book)
            db.session.flush()

            book.genres = [genre_map[name] for name in book_data.get("genres", [])]

            for tag_name in book_data.get("tags", []):
                tag = tag_map.get(tag_name)
                if tag is None:
                    tag = Tag.query.filter_by(name=tag_name).first()
                if tag is None:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                    db.session.flush()
                tag_map[tag_name] = tag
                book.tags.append(tag)

            book_map[book.title] = book

        for connection_data in MANUAL_CONNECTIONS_DATA:
            book_a = book_map[connection_data["book_a"]]
            book_b = book_map[connection_data["book_b"]]

            if book_a.id > book_b.id:
                book_a, book_b = book_b, book_a

            connection = Connection(
                book_a_id=book_a.id,
                book_b_id=book_b.id,
                type="manual",
                note=connection_data["note"],
            )
            db.session.add(connection)

        db.session.commit()
        print(
            f"Seed concluído: {len(BOOKS_DATA)} livros, "
            f"{len(GENRES_DATA)} gêneros, "
            f"{len(MANUAL_CONNECTIONS_DATA)} conexões manuais"
        )


if __name__ == "__main__":
    seed()
