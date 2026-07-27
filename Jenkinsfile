pipeline {
    agent any

    environment {
        TARGET_SERVER = '192.168.1.199'
        TARGET_USER = 'deployer'

        // 3000 is already taken by another project (qminh) on this host.
        APP_PORT = '3001'

        DEPLOY_PATH = '/opt/webapps/cdss'

        // Keepalive probes stop the connection from being dropped as "idle"
        // during quiet stretches of a long remote command like a Docker build.
        SSH_OPTS = '-o StrictHostKeyChecking=no -o ServerAliveInterval=15 -o ServerAliveCountMax=6 -o ConnectTimeout=10'

        // Names this deploy's isolated stack (cdss-<VERSION>) -- see
        // deploy/provision_stack.sh. BUILD_NUMBER is unique and monotonically
        // increasing, which prune_old_stacks.sh relies on to find the oldest
        // stacks to remove.
        VERSION = "${BUILD_NUMBER}"
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
                             backups/backup.sql backups/seed.sql; do
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
                            --exclude 'deploy/.current_version' \
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
                                sed -i 's/\\r\$//' ${DEPLOY_PATH}/.env.new
                                mv -f ${DEPLOY_PATH}/.env.new ${DEPLOY_PATH}/.env
                            "
                        '''
                    }
                }
            }
        }

        // Builds a brand-new stack (cdss-${VERSION}: its own db + backend
        // container, network, and volume) and migrates/seeds it, entirely
        // side by side with whatever is currently live. The live stack is
        // never touched in this stage -- a failure here means production
        // keeps running untouched.
        stage('Provision New Stack') {
            steps {
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/provision_stack.sh
                            ./deploy/provision_stack.sh ${VERSION}
                        "
                    '''
                }
            }
        }

        // Stops the previously-live stack, starts the new stack's frontend
        // on the now-free public port, and health-checks it. If that check
        // fails, deploy/promote_stack.sh itself restarts the old stack
        // before exiting non-zero, so the site is back up within one
        // health-check cycle rather than staying down.
        stage('Promote New Stack') {
            steps {
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/promote_stack.sh
                            ./deploy/promote_stack.sh ${VERSION}
                        "
                    '''
                }
            }
        }

        stage('Prune Old Stacks') {
            steps {
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/prune_old_stacks.sh
                            ./deploy/prune_old_stacks.sh
                        "
                    '''
                }
            }
        }
    }

    post {

        success {
            echo 'Deployment successful'
            echo "cdss running on ${TARGET_SERVER}:${APP_PORT} (version ${VERSION})"
        }

        failure {
            echo 'Deployment failed - check the failing stage log above.'
            echo 'Tearing down the failed new stack, if any was created; the previous version was never stopped for good and keeps serving traffic (promote_stack.sh restarts it automatically if the failure happened after the port handover).'
            sshagent(['ubuntu-vm-jenkins']) {
                sh '''
                    ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                        cd ${DEPLOY_PATH} 2>/dev/null && docker compose -p cdss-${VERSION} -f docker-compose.prod.yml down -v --rmi all || true
                    "
                '''
            }
        }

        always {
            cleanWs()
        }
    }
}
