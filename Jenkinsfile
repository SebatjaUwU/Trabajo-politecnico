// Pipeline de integración continua de la API de notas
// Énfasis Profesional I (Integración Continua) – Entrega 2 · Politécnico Grancolombiano
//
// Etapas: Checkout -> Verificar herramientas -> Lint y pruebas unitarias ->
//         Construir imagen -> Pruebas de integración -> Desplegar
// Jenkins corre en Docker (carpeta jenkins/) y usa el Docker del equipo anfitrión.

pipeline {
    agent any

    parameters {
        booleanParam(name: 'DESPLEGAR', defaultValue: true,
                     description: 'Si las pruebas pasan, actualizar el sistema real (proyecto trabajo-politecnico) en el equipo')
    }

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '15'))
        disableConcurrentBuilds()
        skipDefaultCheckout()   // el checkout se hace en la primera etapa
    }

    // Revisa GitHub cada ~5 minutos; si hay commits nuevos, ejecuta el pipeline.
    // (Un webhook de GitHub no llega a un Jenkins en localhost sin exponerlo a internet.)
    triggers {
        pollSCM('H/5 * * * *')
    }

    environment {
        // Copia aislada para pruebas: nombre de proyecto único por build y sin puertos publicados
        COMPOSE_CI   = "docker compose -p notas-ci-${BUILD_NUMBER} -f docker-compose.yml -f docker-compose.ci.yml"
        // Sistema "real": el mismo proyecto que se levantó a mano en la Entrega 1
        COMPOSE_PROD = 'docker compose -p trabajo-politecnico'
    }

    stages {
        stage('Checkout') {
            steps {
                script {
                    def scmVars = checkout scm
                    env.RAMA = scmVars.GIT_BRANCH ?: 'desconocida'
                }
                sh 'git log -1 --pretty="Commit %h de %an: %s"'
                echo "Rama: ${env.RAMA}"
            }
        }

        stage('Verificar herramientas') {
            steps {
                sh '''
                    docker version --format 'Docker Engine {{.Server.Version}}'
                    docker compose version
                    python3 --version
                '''
            }
        }

        stage('Lint y pruebas unitarias') {
            steps {
                dir('app') {
                    sh '''
                        python3 -m venv .venv
                        . .venv/bin/activate
                        pip install --quiet --disable-pip-version-check -r requirements-dev.txt
                        echo "--- flake8 (estilo del código) ---"
                        flake8
                        echo "--- pytest (pruebas unitarias con BD simulada) ---"
                        pytest -v --junitxml=reportes/junit.xml
                    '''
                }
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'app/reportes/junit.xml'
                }
            }
        }

        stage('Construir imagen') {
            steps {
                // Credenciales temporales solo para la copia de pruebas (el .env real nunca está en el repo)
                sh '''
                    cp .env.example .env
                    CLAVE="ci_$(head -c 12 /dev/urandom | od -An -tx1 | tr -d ' \\n')"
                    sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${CLAVE}/" .env
                '''
                sh "${COMPOSE_CI} build app"
                sh "docker tag notas-ci-${BUILD_NUMBER}-app notas-app:build-${BUILD_NUMBER}"
                sh "docker image ls notas-app"
            }
        }

        stage('Pruebas de integración') {
            steps {
                // --wait: espera a que db esté healthy y app en ejecución
                sh "${COMPOSE_CI} up -d --wait"
                sh "${COMPOSE_CI} ps"
                // La prueba corre dentro del contenedor app: guarda una nota y la lee desde PostgreSQL
                sh "${COMPOSE_CI} exec -T app python - < ci/prueba_integracion.py"
                // Evidencia directa en la base de datos
                sh "${COMPOSE_CI} exec -T db sh -c 'psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -c \"SELECT * FROM notas;\"'"
            }
        }

        stage('Desplegar') {
            when {
                allOf {
                    expression { params.DESPLEGAR }
                    expression { env.RAMA in ['origin/main', 'main', 'refs/heads/main'] }
                }
            }
            steps {
                // .env real guardado como credencial "Secret file" en Jenkins (id: notas-env)
                withCredentials([file(credentialsId: 'notas-env', variable: 'ENV_REAL')]) {
                    sh 'cp "$ENV_REAL" .env'
                    sh "${COMPOSE_PROD} up -d --build"
                    sh "${COMPOSE_PROD} ps"
                    // Comprobación posterior al despliegue (no crea notas en el sistema real)
                    sh "${COMPOSE_PROD} exec -T app python - --solo-salud < ci/prueba_integracion.py"
                }
            }
        }
    }

    post {
        always {
            sh "${COMPOSE_CI} logs --no-color > compose-ci.log 2>&1 || true"
            archiveArtifacts artifacts: 'compose-ci.log', allowEmptyArchive: true
            // Limpieza: borra contenedores, red y volumen de la copia de pruebas
            sh "${COMPOSE_CI} down -v --remove-orphans --rmi local || true"
            sh 'rm -f .env'
        }
        success {
            echo "Build ${BUILD_NUMBER} OK: código revisado, imagen construida, contenedores comunicados y probados."
        }
        failure {
            echo "Build ${BUILD_NUMBER} FALLÓ: revisa la etapa en rojo y el archivo compose-ci.log."
        }
    }
}
