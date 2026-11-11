"""API de notas: contenedor "app".

Se conecta al contenedor "db" (PostgreSQL) usando el NOMBRE DEL SERVICIO
definido en docker-compose.yml (DB_HOST=db), nunca una IP fija.
"""
import os
import time

import psycopg2
from flask import Flask, jsonify, request

app = Flask(__name__)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "db"),
    "port": int(os.environ.get("DB_PORT", "5432")),
    "dbname": os.environ["POSTGRES_DB"],
    "user": os.environ["POSTGRES_USER"],
    "password": os.environ["POSTGRES_PASSWORD"],
}


def conectar():
    return psycopg2.connect(**DB_CONFIG)


def inicializar_bd(intentos=10, espera=2):
    """Crea la tabla si no existe. Reintenta por si la BD aún está arrancando."""
    for i in range(1, intentos + 1):
        try:
            with conectar() as conn, conn.cursor() as cur:
                # gunicorn arranca 2 workers a la vez: el candado evita que ambos
                # creen la tabla al mismo tiempo (error UniqueViolation en pg_type).
                cur.execute("SELECT pg_advisory_xact_lock(4242)")
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS notas (
                        id SERIAL PRIMARY KEY,
                        texto VARCHAR(200) NOT NULL,
                        creada TIMESTAMP DEFAULT NOW()
                    )
                    """
                )
            print(f"[app] Conectado a {DB_CONFIG['host']}:{DB_CONFIG['port']} - tabla lista", flush=True)
            return
        except psycopg2.OperationalError as e:
            print(f"[app] BD no disponible (intento {i}/{intentos}): {e}".strip(), flush=True)
            time.sleep(espera)
    raise RuntimeError("No se pudo conectar a la base de datos")


@app.get("/")
def inicio():
    return jsonify(
        servicio="api-notas",
        endpoints=["GET /salud", "POST /notas", "GET /notas", "GET /notas/<id>"],
    )


@app.get("/salud")
def salud():
    """Comprueba la comunicación app -> db."""
    try:
        with conectar() as conn, conn.cursor() as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
        return jsonify(app="ok", db="ok", db_host=DB_CONFIG["host"], db_version=version)
    except Exception as e:  # noqa: BLE001
        return jsonify(app="ok", db="error", detalle=str(e)), 503


@app.post("/notas")
def crear_nota():
    datos = request.get_json(silent=True) or {}
    texto = (datos.get("texto") or "").strip()
    if not texto:
        return jsonify(error="Envía JSON con el campo 'texto'"), 400
    with conectar() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO notas (texto) VALUES (%s) RETURNING id, creada", (texto,))
        nota_id, creada = cur.fetchone()
    return jsonify(id=nota_id, texto=texto, creada=creada.isoformat()), 201


@app.get("/notas")
def listar_notas():
    with conectar() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, texto, creada FROM notas ORDER BY id")
        filas = cur.fetchall()
    return jsonify([{"id": f[0], "texto": f[1], "creada": f[2].isoformat()} for f in filas])


@app.get("/notas/<int:nota_id>")
def obtener_nota(nota_id):
    with conectar() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, texto, creada FROM notas WHERE id = %s", (nota_id,))
        f = cur.fetchone()
    if not f:
        return jsonify(error=f"La nota {nota_id} no existe"), 404
    return jsonify(id=f[0], texto=f[1], creada=f[2].isoformat())


inicializar_bd()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
