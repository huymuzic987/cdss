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

    options {
        // Checkout is performed explicitly below; avoid Declarative
        // Pipeline's otherwise automatic duplicate checkout.
        skipDefaultCheckout(true)
        // Two deployments must never build/migrate/promote on the same host
        // at once. A queued newer build waits instead of doubling host load.
        disableConcurrentBuilds()
        timestamps()
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
                             backups/backup.sql backups/seed.sql \
                             deploy/backup_db.sh deploy/backup_current_db.sh \
                             deploy/build_images.sh deploy/seed_database.sh \
                             deploy/lib.sh deploy/provision_stack.sh \
                             deploy/promote_stack.sh deploy/prune_old_stacks.sh; do
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

                        # The target is on the same LAN. Compression consumes
                        # more CPU than it saves for already-compressed build
                        # inputs and was slowing both Jenkins and production.
                        rsync -a --delete \
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
                            --exclude 'deploy/.build_state' \
                            --exclude 'deploy/.router_drain_pending' \
                            --exclude 'persistent-backups' \
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

        // Build both application images once and in parallel after the new
        // source and production environment have reached the target host.
        // Provision and promotion reuse these exact images.
        stage('Build Images') {
            steps {
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/build_images.sh
                            ./deploy/build_images.sh ${VERSION}
                        "
                    '''
                }
            }
        }

        // Takes a plain-SQL dump of the currently-live database before any
        // new stack is provisioned. The dump is written to the persistent
        // host backup directory, outside all per-version Docker volumes.
        stage('Backup Current Database') {
            steps {
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/backup_current_db.sh deploy/backup_db.sh
                            ./deploy/backup_current_db.sh
                        "
                    '''
                }
            }
        }

        // Creates an isolated database volume, clones the live database into
        // it, then migrates and seeds it without changing tree_layouts.
        // Production remains online throughout this stage.
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

        // Atomically reloads the stable router after the new private frontend
        // is healthy. The router owns APP_PORT continuously; if post-switch
        // checks fail, promote_stack.sh restores its previous configuration
        // without stopping the old release.
        stage('Promote New Stack') {
            steps {
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/promote_stack.sh
                            PUBLIC_APP_PORT=${APP_PORT} ./deploy/promote_stack.sh ${VERSION}
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
            echo 'Tearing down the failed candidate stack if it was not promoted. The stable router keeps the last successful release serving throughout.'
            sshagent(['ubuntu-vm-jenkins']) {
                sh '''
                    ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                        cd ${DEPLOY_PATH} 2>/dev/null || exit 0
                        current_version=\$(cat deploy/.current_version 2>/dev/null || true)
                        if [ \"\$current_version\" != \"${VERSION}\" ]; then
                            docker compose -p cdss-${VERSION} -f docker-compose.prod.yml down -v --rmi all || true
                        else
                            echo \"Version ${VERSION} is already live; leaving it running despite a later pipeline failure.\"
                        fi
                    "
                '''
            }
        }

        always {
            cleanWs()
        }
    }
}
