"""Configuración de las pruebas unitarias.

Las pruebas unitarias NO necesitan PostgreSQL: se reemplaza psycopg2.connect
por una base de datos falsa en memoria. Así Jenkins puede ejecutarlas en
segundos, antes de construir las imágenes. La comunicación real app -> db
se prueba después, en la etapa de integración (ci/prueba_integracion.py).
"""
import datetime
import os
import sys
from unittest import mock

import pytest

# app.py lee estas variables al importarse
os.environ.setdefault("POSTGRES_DB", "notasdb_test")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class BDFalsa:
    """Imita lo mínimo de PostgreSQL que usa app.py."""

    def __init__(self):
        self.notas = []
        self.caida = False

    def conectar(self, **_kwargs):
        import psycopg2

        if self.caida:
            raise psycopg2.OperationalError("could not connect to server: db")
        return ConexionFalsa(self)


class ConexionFalsa:
    def __init__(self, bd):
        self.bd = bd

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return CursorFalso(self.bd)


class CursorFalso:
    def __init__(self, bd):
        self.bd = bd
        self.resultado = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        sql = " ".join(sql.split()).upper()
        if sql.startswith("SELECT VERSION()"):
            self.resultado = [("PostgreSQL 16 (falso)",)]
        elif sql.startswith("INSERT INTO NOTAS"):
            nota = (len(self.bd.notas) + 1, params[0], datetime.datetime(2026, 11, 24, 12, 0))
            self.bd.notas.append(nota)
            self.resultado = [(nota[0], nota[2])]
        elif sql.startswith("SELECT ID, TEXTO, CREADA FROM NOTAS WHERE"):
            self.resultado = [n for n in self.bd.notas if n[0] == params[0]]
        elif sql.startswith("SELECT ID, TEXTO, CREADA FROM NOTAS"):
            self.resultado = list(self.bd.notas)
        else:  # CREATE TABLE, pg_advisory_xact_lock
            self.resultado = []

    def fetchone(self):
        return self.resultado[0] if self.resultado else None

    def fetchall(self):
        return self.resultado


@pytest.fixture
def bd():
    return BDFalsa()


@pytest.fixture
def cliente(bd):
    with mock.patch("psycopg2.connect", side_effect=bd.conectar):
        sys.modules.pop("app", None)  # importa app.py de nuevo con la BD falsa
        import app as modulo_app

        modulo_app.app.config["TESTING"] = True
        yield modulo_app.app.test_client()
