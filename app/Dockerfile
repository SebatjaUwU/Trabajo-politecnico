# Imagen base oficial y ligera de Python (variante slim: ~50 MB frente a ~1 GB de la completa)
FROM python:3.12-slim

# Evita archivos .pyc y muestra los logs al instante
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Primero solo las dependencias: Docker reutiliza esta capa en caché
# mientras requirements.txt no cambie, y las reconstrucciones son rápidas.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Usuario sin privilegios (buena práctica de seguridad)
RUN useradd --create-home appuser
USER appuser

EXPOSE 5000

# gunicorn: servidor WSGI de producción en lugar del servidor de desarrollo de Flask
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
