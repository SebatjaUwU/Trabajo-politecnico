"""Prueba de integración: se ejecuta DENTRO del contenedor app desde Jenkins.

    docker compose exec -T app python - < ci/prueba_integracion.py
    docker compose exec -T app python - --solo-salud < ci/prueba_integracion.py

Comprueba con contenedores reales que la app habla con PostgreSQL por el
nombre de servicio "db": guarda una nota y la vuelve a leer.
Solo usa la biblioteca estándar de Python (no instala nada en la imagen).
"""
import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://localhost:5000"
fallos = 0


def pedir(metodo, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(BASE + ruta, data=datos, method=metodo,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def comprobar(descripcion, condicion):
    global fallos
    print(("  [OK]    " if condicion else "  [FALLA] ") + descripcion, flush=True)
    if not condicion:
        fallos += 1


def esperar_app(segundos=60):
    limite = time.time() + segundos
    while time.time() < limite:
        try:
            estado, cuerpo = pedir("GET", "/salud")
            if estado == 200:
                return cuerpo
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(2)
    print("  [FALLA] la app no respondió /salud en", segundos, "s")
    sys.exit(1)


print("== Prueba de integración app <-> db ==")
salud = esperar_app()
comprobar("GET /salud -> db=ok", salud.get("db") == "ok")
comprobar("la app usa el host 'db' (nombre del servicio)", salud.get("db_host") == "db")
print("      ", salud.get("db_version", "")[:60])

if "--solo-salud" not in sys.argv:
    texto = f"Nota de Jenkins {time.strftime('%Y-%m-%d %H:%M:%S')}"
    estado, nota = pedir("POST", "/notas", {"texto": texto})
    comprobar(f"POST /notas -> 201 (id={nota.get('id') if nota else None})", estado == 201)

    estado, leida = pedir("GET", f"/notas/{nota['id']}")
    comprobar("GET /notas/<id> devuelve el mismo texto", estado == 200 and leida["texto"] == texto)

    estado, lista = pedir("GET", "/notas")
    comprobar("GET /notas incluye la nota", any(n["id"] == nota["id"] for n in lista))

    estado, _ = pedir("POST", "/notas", {"texto": ""})
    comprobar("POST /notas sin texto -> 400", estado == 400)

    estado, _ = pedir("GET", "/notas/999999")
    comprobar("GET /notas/999999 -> 404", estado == 404)

print("== Resultado:", "TODO OK" if fallos == 0 else f"{fallos} comprobación(es) fallida(s)", "==")
sys.exit(1 if fallos else 0)
