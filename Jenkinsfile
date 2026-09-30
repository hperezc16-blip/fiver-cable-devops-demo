// Fiver Cable - Pipeline CI/CD equivalente para Jenkins
// Etapas: Checkout -> Build -> Test -> Deploy Staging
// Requiere un agente con Docker, Docker Compose, Python 3.11 y Google Chrome.
pipeline {
    agent any
    options { timestamps(); timeout(time: 30, unit: 'MINUTES') }
    environment {
        REPORTS_DIR = 'reports'
        HEADLESS    = '1'
        JWT_SECRET  = credentials('fivercable-jwt-secret')
    }
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Build') {
            steps {
                sh '''
                    python3 -m venv .venv && . .venv/bin/activate
                    pip install -r requirements-dev.txt
                    ruff check src tests
                    mkdir -p $REPORTS_DIR
                    python -m pytest -m unit --junitxml=$REPORTS_DIR/junit-unit.xml
                    docker compose build
                '''
            }
        }
        stage('Test') {
            steps {
                sh '''
                    . .venv/bin/activate
                    docker compose up -d --wait
                    python -m pytest --junitxml=$REPORTS_DIR/junit.xml \
                        --html=$REPORTS_DIR/reporte-pruebas.html --self-contained-html \
                        --cov=src --cov-report=xml:$REPORTS_DIR/coverage.xml
                '''
            }
            post {
                always {
                    junit "${REPORTS_DIR}/junit*.xml"
                    archiveArtifacts artifacts: "${REPORTS_DIR}/**", allowEmptyArchive: true
                    sh 'docker compose down -v'
                }
            }
        }
        stage('Deploy Staging') {
            when { branch 'main' }
            steps {
                sh '''
                    . .venv/bin/activate
                    docker compose -p fivercable-staging up -d --build --wait
                    python -m pytest -m system --junitxml=$REPORTS_DIR/junit-smoke.xml
                '''
            }
        }
    }
    post {
        failure { echo 'Pipeline fallido: revisar la pestaña Test Results y los logs de los servicios.' }
    }
}
