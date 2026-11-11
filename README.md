# API de Notas en dos contenedores Docker

Proyecto de la **Entrega 1 – Énfasis Profesional I (Integración Continua)**, Politécnico Grancolombiano.

Una API web sencilla para **guardar y consultar notas**, dividida en dos contenedores que se comunican por una red de Docker:

| Contenedor | Servicio | Imagen | Función |
|---|---|---|---|
| `notas-app` | `app` | **Propia** (`app/Dockerfile`, basada en `python:3.12-slim`) | API REST en Flask + gunicorn, puerto 5000 |
| `notas-db` | `db` | **Oficial** `postgres:16-alpine` | Base de datos PostgreSQL que guarda las notas |

```
  Tu navegador / curl
          │  http://localhost:5000
          ▼
 ┌──────────────────── red "red_notas" (bridge) ────────────────────┐
 │                                                                  │
 │   ┌──────────────┐   DB_HOST=db : 5432   ┌──────────────────┐    │
 │   │  notas-app   │ ────────────────────► │    notas-db      │    │
 │   │ Flask:5000   │   (DNS interno Docker)│ PostgreSQL:5432  │    │
 │   └──────────────┘                       └────────┬─────────┘    │
 │                                                   │ volumen      │
 └───────────────────────────────────────────────────┼──────────────┘
                                                     ▼
                                                 datos_db
```

La app **nunca usa una IP fija**: se conecta al host `db`, que es el nombre del servicio en `docker-compose.yml`. Docker resuelve ese nombre a la IP del contenedor dentro de la red `red_notas`. La base de datos no publica puertos al equipo: solo es accesible desde la red interna.

---

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) o Docker Engine + plugin Compose (Linux).
- Git.
- Comprueba con:
  ```bash
  docker --version
  docker compose version
  ```

## Cómo levantar el sistema

```bash
# 1. Clonar el repositorio
git clone https://github.com/<usuario>/<repositorio>.git
cd <repositorio>

# 2. Crear el archivo de credenciales a partir de la plantilla
cp .env.example .env          # Windows PowerShell: copy .env.example .env
#    (opcional) edita .env y cambia POSTGRES_PASSWORD

# 3. Construir la imagen de la app y levantar los dos contenedores
docker compose up -d --build

# 4. Verificar que ambos están corriendo (db debe decir "healthy")
docker compose ps
```

### Variables del archivo `.env`

El archivo `.env` **no se sube a GitHub** (está en `.gitignore`). Debes crearlo con estas variables:

| Variable | Ejemplo | Para qué |
|---|---|---|
| `POSTGRES_DB` | `notasdb` | Nombre de la base de datos que crea PostgreSQL |
| `POSTGRES_USER` | `notas_user` | Usuario de la base de datos |
| `POSTGRES_PASSWORD` | `cambia_esta_clave` | Contraseña de ese usuario |
| `APP_PORT` | `5000` | (Opcional) puerto del equipo donde queda la API |

## Operación de ejemplo: guardar una nota y consultarla

**1. Comprobar la comunicación app → db**

```bash
curl http://localhost:5000/salud
```
Resultado esperado:
```json
{"app":"ok","db":"ok","db_host":"db","db_version":"PostgreSQL 16.x ..."}
```

**2. Guardar una nota** (la app la inserta en el contenedor `db`)

```bash
curl -X POST http://localhost:5000/notas \
     -H "Content-Type: application/json" \
     -d '{"texto":"Hola desde Docker"}'
```
Resultado esperado (código 201):
```json
{"creada":"2026-11-10T19:48:18.471022","id":1,"texto":"Hola desde Docker"}
```

**3. Consultarla** (la app la lee del contenedor `db`)

```bash
curl http://localhost:5000/notas
curl http://localhost:5000/notas/1
```
Resultado esperado:
```json
[{"creada":"2026-11-10T19:48:18.471022","id":1,"texto":"Hola desde Docker"}]
```

> **Windows PowerShell:** `curl` es un alias distinto. Usa `curl.exe` con las comillas escapadas, o:
> ```powershell
> Invoke-RestMethod -Method Post -Uri http://localhost:5000/notas -ContentType "application/json" -Body '{"texto":"Hola desde Docker"}'
> Invoke-RestMethod http://localhost:5000/notas
> ```

**4. (Opcional) Ver el dato directamente dentro de la base de datos**

```bash
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT * FROM notas;"'
```

### Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Lista de endpoints |
| GET | `/salud` | Estado de la app y de la conexión con la BD |
| POST | `/notas` | Crea una nota. Cuerpo: `{"texto": "..."}` |
| GET | `/notas` | Lista todas las notas |
| GET | `/notas/<id>` | Consulta una nota (404 si no existe) |

## Red y orden de arranque

- **Red:** `docker-compose.yml` define la red `red_notas` (driver `bridge`) y conecta ambos servicios. Dentro de ella cada contenedor se encuentra por el **nombre de su servicio** (`app`, `db`). Puedes inspeccionarla con:
  ```bash
  docker network ls
  docker network inspect <repositorio>_red_notas
  ```
- **Orden de arranque:** `db` tiene un `healthcheck` con `pg_isready`. La `app` declara `depends_on: db: condition: service_healthy`, así que Compose **no arranca la app hasta que PostgreSQL acepta conexiones**. Además, la app reintenta la conexión hasta 10 veces al iniciar, por si la BD se reinicia.
- **Persistencia:** las notas se guardan en el volumen `datos_db`, así que sobreviven a `docker compose down`. Para borrarlas: `docker compose down -v`.

## Comandos útiles

```bash
docker compose logs -f app     # ver logs de la app
docker compose logs db         # ver logs de la base de datos
docker compose ps              # estado de los contenedores
docker compose down            # detener y eliminar contenedores (conserva datos)
docker compose down -v         # además borra el volumen con los datos
```

## Errores comunes y solución

| Síntoma | Causa | Solución |
|---|---|---|
| `env file .env not found` | No creaste el `.env` | `cp .env.example .env` |
| `Bind for 0.0.0.0:5000 failed: port is already allocated` | Otro programa usa el puerto 5000 (en macOS suele ser AirPlay) | Cambia `APP_PORT=5001` en `.env` y usa `http://localhost:5001` |
| `Cannot connect to the Docker daemon` / `error during connect` | Docker Desktop no está abierto | Abre Docker Desktop y espera a que diga *Running* |
| `/salud` responde `"db":"error"` con `password authentication failed` | Cambiaste la contraseña en `.env` después del primer arranque; PostgreSQL solo la lee al crear el volumen | `docker compose down -v` y luego `docker compose up -d --build` |
| `could not translate host name "db"` | Ejecutaste `app.py` fuera de Docker, o los servicios no están en la misma red | Levanta todo con `docker compose up`; no ejecutes la app suelta |
| La app se reinicia en bucle al inicio | La BD aún no estaba lista | Revisa `docker compose logs db`; el healthcheck y los reintentos lo resuelven en segundos |
| `curl` en PowerShell da error con `-H` o `-d` | `curl` es un alias de `Invoke-WebRequest` | Usa `curl.exe` o `Invoke-RestMethod` (ver arriba) |

## Estructura

```
.
├── app/
│   ├── app.py            # API Flask
│   ├── requirements.txt  # dependencias de Python
│   ├── Dockerfile        # imagen propia de la app
│   └── .dockerignore
├── docker-compose.yml    # define los 2 contenedores, la red y el volumen
├── .env.example          # plantilla de credenciales (el .env real no se sube)
├── .gitignore
└── README.md
```

## Integrantes

| Nombre | Usuario GitHub | Aporte |
|---|---|---|
| _Integrante 1_ | `@usuario1` | |
| _Integrante 2_ | `@usuario2` | |
| _Integrante 3_ | `@usuario3` | |
