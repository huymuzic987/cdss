pipeline {
    agent any

    environment {
        TARGET_SERVER = '192.168.1.199'
        TARGET_USER = 'deployer'

        APP_NAME = 'cdss'
        APP_PORT = '3000'

        DEPLOY_PATH = '/opt/webapps/cdss'

        // Keepalive probes stop the connection from being dropped as "idle"
        // during quiet stretches of a long remote command like a Docker build.
        SSH_OPTS = '-o StrictHostKeyChecking=no -o ServerAliveInterval=15 -o ServerAliveCountMax=6 -o ConnectTimeout=10'

        COMPOSE = 'docker compose -f docker-compose.prod.yml'
    }

    triggers {
        githubPush()
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Checking out source code...'
                checkout scm
            }
        }

        stage('Verify Files') {
            steps {
                sh '''
                    echo "=== Jenkins Build Info ==="
                    pwd
                    ls -la

                    for f in pyproject.toml uv.lock frontend/package.json frontend/pnpm-lock.yaml \
                             Dockerfile.backend frontend/Dockerfile docker-compose.prod.yml; do
                        if [ ! -f "$f" ]; then
                            echo "ERROR: required file missing: $f"
                            exit 1
                        fi
                    done

                    echo "Git commit:"
                    git log -1 --oneline
                '''
            }
        }

        stage('Test & Audit') {
            parallel {
                stage('Backend') {
                    steps {
                        // Runs as root inside the container (needed to install uv), so
                        // it chowns the bind-mounted workspace back to the Jenkins
                        // agent's user at the end - otherwise root-owned .venv/
                        // artifacts left behind would break the post-build cleanWs().
                        sh '''
                            docker run --rm \
                                -v "$WORKSPACE":/workspace -w /workspace \
                                -v cdss-uv-cache:/root/.cache/uv \
                                -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
                                python:3.12-slim sh -c '
                                    set -e
                                    pip install --quiet --no-cache-dir uv
                                    uv sync --frozen --group dev
                                    uv run ruff check .
                                    uv run ruff format --check .
                                    uv run pyright
                                    uv run pytest -m "not database"
                                    uv run --with pip-audit pip-audit
                                    chown -R "$HOST_UID:$HOST_GID" /workspace
                                '
                        '''
                    }
                }
                stage('Frontend') {
                    steps {
                        sh '''
                            docker run --rm \
                                -v "$WORKSPACE/frontend":/app -w /app \
                                -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
                                node:20-alpine sh -c '
                                    set -e
                                    corepack enable
                                    corepack prepare pnpm@9 --activate
                                    pnpm install --frozen-lockfile
                                    pnpm lint
                                    pnpm build
                                    pnpm audit --audit-level=high
                                    chown -R "$HOST_UID:$HOST_GID" /app
                                '
                        '''
                    }
                }
            }
        }

        stage('Deploy Files') {
            steps {
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            mkdir -p ${DEPLOY_PATH}
                        "

                        rsync -avz --delete \
                            --exclude '.git' \
                            --exclude '.venv' \
                            --exclude 'node_modules' \
                            --exclude 'frontend/node_modules' \
                            --exclude 'frontend/dist' \
                            --exclude '.env' \
                            --exclude '.env.*' \
                            --exclude '*.log' \
                            --exclude '.pytest_cache' \
                            --exclude '.ruff_cache' \
                            --exclude 'scratch' \
                            ./ ${TARGET_USER}@${TARGET_SERVER}:${DEPLOY_PATH}/
                    '''
                }
            }
        }

        stage('Inject Environment') {
            steps {
                withCredentials([file(credentialsId: 'cdss-prod-env', variable: 'ENV_FILE')]) {
                    sshagent(['ubuntu-vm-jenkins']) {
                        sh '''
                            scp ${SSH_OPTS} $ENV_FILE ${TARGET_USER}@${TARGET_SERVER}:${DEPLOY_PATH}/.env.new
                            ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                                mv -f ${DEPLOY_PATH}/.env.new ${DEPLOY_PATH}/.env
                            "
                        '''
                    }
                }
            }
        }

        stage('Build Images') {
            steps {
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            export IMAGE_TAG=${BUILD_NUMBER}
                            ${COMPOSE} build
                        "
                    '''
                }
            }
        }

        stage('Security Scan') {
            steps {
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            if ! command -v trivy > /dev/null 2>&1; then
                                echo 'WARNING: trivy is not installed on ${TARGET_SERVER}; skipping image scan.'
                                echo 'Install it (https://aquasecurity.github.io/trivy) to enable this gate.'
                                exit 0
                            fi

                            echo 'Scanning backend image...'
                            trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed ${APP_NAME}-backend:${BUILD_NUMBER}

                            echo 'Scanning frontend image...'
                            trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed ${APP_NAME}-frontend:${BUILD_NUMBER}
                        "
                    '''
                }
            }
        }

        stage('Database Migration') {
            steps {
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            export IMAGE_TAG=${BUILD_NUMBER}
                            ${COMPOSE} up -d db
                            ${COMPOSE} run --rm backend uv run alembic upgrade head
                        "
                    '''
                }
            }
        }

        stage('Seed Reference Data') {
            steps {
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/seed_reference_data.sh
                            ./deploy/seed_reference_data.sh
                        "
                    '''
                }
            }
        }

        stage('Deploy & Health Check') {
            steps {
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/rollout.sh
                            ./deploy/rollout.sh ${BUILD_NUMBER} ${APP_PORT}
                        "
                    '''
                }
            }
        }

        stage('Cleanup Old Images') {
            steps {
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/cleanup_images.sh
                            ./deploy/cleanup_images.sh
                        "
                    '''
                }
            }
        }
    }

    post {

        success {
            echo 'Deployment successful'
            echo "cdss running on ${TARGET_SERVER}:${APP_PORT}"
        }

        failure {
            echo 'Deployment failed. If containers were already deployed, the pipeline attempted an automatic rollback to the last known-good build - check the "Deploy & Health Check" stage log above.'
        }

        always {
            cleanWs()
        }
    }
}
