pipeline {
    agent any

    environment {
        TARGET_SERVER = '192.168.1.199'
        TARGET_USER = 'deployer'

        APP_PORT = '3000'

        DEPLOY_PATH = '/opt/webapps/cdss'

        // Keepalive probes stop the connection from being dropped as "idle"
        // during quiet stretches of a long remote command like a Docker build.
        SSH_OPTS = '-o StrictHostKeyChecking=no -o ServerAliveInterval=15 -o ServerAliveCountMax=6 -o ConnectTimeout=10'
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
                             Dockerfile.backend frontend/Dockerfile docker-compose.prod.yml \
                             backups/cdss_prod.sql; do
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

        stage('Migrate & Seed Database') {
            steps {
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/migrate_and_seed.sh
                            ./deploy/migrate_and_seed.sh
                        "
                    '''
                }
            }
        }

        stage('Build & Start App') {
            steps {
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/start_app.sh
                            ./deploy/start_app.sh
                        "
                    '''
                }
            }
        }

        stage('Health Check') {
            steps {
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/health_check.sh
                            ./deploy/health_check.sh ${APP_PORT}
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
            echo 'Deployment failed - check the failing stage log above.'
        }

        always {
            cleanWs()
        }
    }
}
