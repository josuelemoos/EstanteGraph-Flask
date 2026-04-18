"""Configurações da aplicação."""

from __future__ import annotations

import os


class Config:
    """Configuração base compartilhada entre os ambientes."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///bookshelf.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    """Configuração para desenvolvimento local."""

    DEBUG = True


class TestingConfig(Config):
    """Configuração para testes."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")


class ProductionConfig(Config):
    """Configuração para produção."""

    DEBUG = False


def get_config() -> type[Config]:
    """Retorna a classe de configuração conforme o ambiente."""

    env = os.getenv("FLASK_ENV", "development").lower()
    mapping = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }
    return mapping.get(env, DevelopmentConfig)
