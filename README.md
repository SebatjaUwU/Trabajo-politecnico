# API de Notas en dos contenedores Docker

Proyecto de **Énfasis Profesional I (Integración Continua)**, Politécnico Grancolombiano.

- **Entrega 1:** dos contenedores comunicados con Docker.
- **Entrega 2:** integración continua con **Jenkins** (ver [Integración continua con Jenkins](#integración-continua-con-jenkins-entrega-2)).

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
git clone https://github.com/SebatjaUwU/Trabajo-politecnico.git
cd Trabajo-politecnico

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
docker compose exec db psql -U notas_user -d notasdb -c "SELECT * FROM notas;"
```
Resultado esperado:
```
 id |       texto       |           creada
----+-------------------+----------------------------
  1 | Hola desde Docker | 2026-11-11 01:15:45.136786
(1 row)
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

## Integración continua con Jenkins (Entrega 2)

Jenkins corre en su propio contenedor y usa el Docker del equipo para construir y probar el proyecto. Cada vez que hay un commit nuevo en `main`, ejecuta el `Jenkinsfile`:

```
 GitHub ──(pollSCM cada ~5 min)──► Jenkins (contenedor, puerto 8080)
                                      │  usa /var/run/docker.sock
   1. Checkout                        ▼
   2. Verificar herramientas     Docker del equipo
   3. Lint y pruebas unitarias   ├─ notas-ci-<N>  (copia de pruebas, aislada, se borra al final)
   4. Construir imagen           └─ trabajo-politecnico (sistema real, puerto 5000)
   5. Pruebas de integración
   6. Desplegar (solo main)
```

| Etapa | Qué hace | Si falla |
|---|---|---|
| Checkout | Descarga el commit desde GitHub | No hay acceso al repo |
| Verificar herramientas | Muestra versiones de Docker, Compose y Python | Jenkins no ve el Docker del equipo |
| Lint y pruebas unitarias | `flake8` + 8 pruebas `pytest` con BD simulada; publica el reporte JUnit | Error de estilo o de lógica en `app.py` |
| Construir imagen | Crea un `.env` temporal con clave aleatoria y construye la imagen de la app (`notas-app:build-<N>`) | El `Dockerfile` o `requirements.txt` están mal |
| Pruebas de integración | Levanta app + db en una copia aislada (`docker-compose.ci.yml`), guarda una nota y la lee desde PostgreSQL (`ci/prueba_integracion.py`) | La app no se comunica con la BD |
| Desplegar | Solo en `main` y con `DESPLEGAR` marcado: actualiza el sistema real con el `.env` guardado en Jenkins y comprueba `/salud` | Falta la credencial `notas-env` |

Al final, **siempre** guarda los logs (`compose-ci.log`) y borra los contenedores, la red y el volumen de la copia de pruebas.

### Puesta en marcha (una sola vez)

```bash
# 1. Levantar Jenkins (desde la raíz del repositorio)
cd jenkins
docker compose up -d --build        # la primera vez tarda unos minutos

# 2. Clave inicial del administrador
docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

3. Abre **http://localhost:8080**, pega la clave, elige **Install suggested plugins** y crea tu usuario administrador.
4. **Credencial con el `.env` real** (para la etapa Desplegar): *Manage Jenkins → Credentials → System → Global credentials → Add Credentials*
   - Kind: **Secret file** · File: tu archivo `.env` · ID: **`notas-env`**
5. **Crear el job:** *New Item →* nombre `api-notas` *→ Pipeline → OK*
   - *Pipeline → Definition:* **Pipeline script from SCM** · SCM: **Git**
   - Repository URL: `https://github.com/SebatjaUwU/Trabajo-politecnico.git` · Branch: `*/main` · Script Path: `Jenkinsfile`
   - Guardar y pulsar **Build Now** (la primera ejecución registra el parámetro `DESPLEGAR` y el disparador).
6. Prueba la integración continua: haz un commit cualquiera, súbelo a GitHub y en ≤ 5 minutos Jenkins lanza un build solo.

### Pruebas sin Jenkins

```bash
cd app
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt     # Windows: .venv\Scripts\pip install -r requirements-dev.txt
.venv/bin/flake8 && .venv/bin/pytest -v           # Windows: .venv\Scripts\flake8 ; .venv\Scripts\pytest -v
```

### Errores comunes de Jenkins

| Síntoma | Causa | Solución |
|---|---|---|
| `permission denied ... /var/run/docker.sock` | Jenkins no puede usar el Docker del equipo | El `jenkins/docker-compose.yml` ya usa `user: root`; recrea con `docker compose up -d --force-recreate` |
| `Bind for 0.0.0.0:8080 failed` | Otro programa usa el 8080 | Cambia a `"8081:8080"` en `jenkins/docker-compose.yml` y entra por `http://localhost:8081` |
| `ERROR: notas-env` / `Could not find credentials entry` | No creaste la credencial del `.env` | Paso 4, o ejecuta *Build with Parameters* desmarcando `DESPLEGAR` |
| `Conflict. The container name "/notas-db" is already in use` en Desplegar | El sistema se levantó desde otra carpeta con otro nombre de proyecto | `docker rm -f notas-app notas-db` (los datos quedan en el volumen) y vuelve a ejecutar |
| `/salud` con `password authentication failed` tras desplegar | La credencial `notas-env` tiene otra clave que la del volumen existente | Sube a Jenkins el mismo `.env` que usaste en la Entrega 1 |
| El build no arranca solo tras un commit | `pollSCM` se registra en la primera ejecución | Ejecuta una vez **Build Now** a mano |

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
| `psql` muestra solo `--` y `(1 row)` vacío en PowerShell | PowerShell elimina las comillas dobles internas de `sh -c '..."..."'` y `psql` recibe un `SELECT` vacío | Usa el comando sin comillas anidadas: `docker compose exec db psql -U notas_user -d notasdb -c "SELECT * FROM notas;"` (cambia usuario y base si los cambiaste en `.env`) |
| `curl` en PowerShell da error con `-H` o `-d` | `curl` es un alias de `Invoke-WebRequest` | Usa `curl.exe` o `Invoke-RestMethod` (ver arriba) |

## Estructura

```
.
├── app/
│   ├── app.py               # API Flask
│   ├── requirements.txt     # dependencias de Python
│   ├── requirements-dev.txt # pytest y flake8 (solo para Jenkins)
│   ├── tests/               # pruebas unitarias
│   ├── Dockerfile           # imagen propia de la app
│   └── .dockerignore
├── ci/
│   └── prueba_integracion.py # prueba app <-> db que ejecuta Jenkins
├── jenkins/
│   ├── Dockerfile           # Jenkins LTS + Docker CLI + Python
│   └── docker-compose.yml   # levanta Jenkins en localhost:8080
├── Jenkinsfile              # pipeline de integración continua
├── docker-compose.yml       # define los 2 contenedores, la red y el volumen
├── docker-compose.ci.yml    # ajustes para la copia de pruebas de Jenkins
├── .env.example          # plantilla de credenciales (el .env real no se sube)
├── .gitignore
└── README.md
```

## Autor

| Nombre | Usuario GitHub | Grupo | Tutora |
|---|---|---|---|
| Juan Sebastián Parra Loaiza | `@SebatjaUwU` | B05 | Elizabeth Gómez Yepes |
