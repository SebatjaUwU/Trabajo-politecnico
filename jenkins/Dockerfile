# Imagen de Jenkins para este proyecto: Jenkins LTS oficial + lo que necesita el pipeline
FROM jenkins/jenkins:lts-jdk21

USER root

# Python (para lint y pruebas unitarias) y cliente de Docker + plugin Compose
# (para construir y levantar los contenedores usando el Docker del equipo anfitrión)
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl gnupg python3 python3-venv python3-pip \
 && install -m 0755 -d /etc/apt/keyrings \
 && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
      > /etc/apt/sources.list.d/docker.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
 && rm -rf /var/lib/apt/lists/*

USER jenkins

# Plugins que usa el Jenkinsfile (se instalan al construir la imagen)
RUN jenkins-plugin-cli --plugins \
    workflow-aggregator \
    git \
    github \
    junit \
    credentials-binding \
    timestamper \
    pipeline-stage-view
