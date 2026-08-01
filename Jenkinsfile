pipeline {
    agent any

    environment {
        TARGET_SERVER = '192.168.1.199'
        TARGET_USER = 'deployer'

        // 3000 is already taken by another project (qminh) on this host.
        APP_PORT = '3001'
        PUBLIC_URL = 'https://cdss.click'

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

    parameters {
        string(
            name: 'NOTIFICATION_EMAILS',
            defaultValue: 'phamlequangminh2411@gmail.com',
            trim: true,
            description: 'Comma-separated addresses that receive a detailed report for every build. Commit authors, culprits, and the manual build requester are also included when Jenkins knows their email addresses.'
        )
    }

    options {
        // Checkout is performed explicitly below; avoid Declarative
        // Pipeline's otherwise automatic duplicate checkout.
        skipDefaultCheckout(true)
        // Two deployments must never build/migrate/promote on the same host
        // at once. A queued newer build waits instead of doubling host load.
        disableConcurrentBuilds()
        // Retain enough history for trend analysis without unbounded controller
        // disk growth. Test/deployment artifacts receive a smaller cap.
        buildDiscarder(logRotator(
            daysToKeepStr: '30',
            numToKeepStr: '50',
            artifactDaysToKeepStr: '14',
            artifactNumToKeepStr: '20'
        ))
        // A hung Docker, SSH, or database operation must not occupy the only
        // deployment executor indefinitely.
        timeout(time: 90, unit: 'MINUTES')
        // Restarting midway through a stateful deployment can bypass required
        // backup, write-lock, or verification stages.
        disableRestartFromStage()
        skipStagesAfterUnstable()
        timestamps()
    }

    stages {

        stage('Checkout') {
            options { timeout(time: 5, unit: 'MINUTES') }
            steps {
                script { env.CDSS_CURRENT_STAGE = env.STAGE_NAME }
                echo 'Checking out source code...'
                checkout scm
            }
        }

        stage('Verify Files') {
            options { timeout(time: 3, unit: 'MINUTES') }
            steps {
                script { env.CDSS_CURRENT_STAGE = env.STAGE_NAME }
                sh '''
                    echo "=== Jenkins Build Info ==="
                    pwd
                    ls -la

                    if [ "$(uname -s)" != "Linux" ]; then
                        echo "ERROR: CDSS requires a Linux Jenkins agent." >&2
                        exit 1
                    fi
                    for required_command in \
                        bash docker git ssh scp rsync curl awk sed grep tr tail seq cut sha256sum; do
                        if ! command -v "$required_command" > /dev/null 2>&1; then
                            echo "ERROR: Jenkins agent is missing required command: $required_command" >&2
                            exit 1
                        fi
                    done
                    if ! docker info > /dev/null 2>&1; then
                        echo "ERROR: Jenkins agent cannot access the Docker daemon." >&2
                        exit 1
                    fi

                    for f in pyproject.toml uv.lock frontend/package.json frontend/pnpm-lock.yaml \
                             Dockerfile.backend frontend/Dockerfile docker-compose.prod.yml \
                             backups/backup.sql backups/seed.sql \
                             deploy/backup_db.sh deploy/backup_current_db.sh \
                             deploy/build_images.sh deploy/seed_database.sh \
                             deploy/lib.sh deploy/provision_stack.sh \
                             deploy/promote_stack.sh deploy/prune_old_stacks.sh \
                             deploy/cleanup_failed_stack.sh \
                             deploy/ensure_live_route.sh \
                             deploy/render_router_config.sh \
                             deploy/set_write_lock.sh \
                             deploy/run_quality_gates.sh \
                             deploy/run_frontend_quality_gates.sh \
                             scripts/generate_pregnancy_fhir_presets.py; do
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

        // Runs entirely on the Jenkins agent, before the deploy target is
        // touched: pytest (including the database-backed integration tests,
        // against a disposable PostgreSQL container), ruff, pyright, and
        // the frontend's vitest/oxlint/build. A failure here stops the
        // pipeline, so promotion of a broken build is impossible.
        stage('Quality Gates') {
            options { timeout(time: 35, unit: 'MINUTES') }
            steps {
                script { env.CDSS_CURRENT_STAGE = env.STAGE_NAME }
                sh '''
                    chmod +x deploy/run_quality_gates.sh
                    ./deploy/run_quality_gates.sh
                '''
            }
            post {
                always {
                    junit(
                        testResults: '.ci-reports/backend/junit.xml,frontend/.ci-reports/junit.xml',
                        allowEmptyResults: true
                    )
                }
            }
        }

        stage('Deploy Files') {
            options { timeout(time: 10, unit: 'MINUTES') }
            steps {
                script { env.CDSS_CURRENT_STAGE = env.STAGE_NAME }
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
                            --exclude 'deploy/.deployment_state' \
                            --exclude 'deploy/.build_state' \
                            --exclude 'deploy/.router_drain_pending' \
                            --exclude 'deploy/.write_lock' \
                            --exclude 'persistent-backups' \
                            ./ ${TARGET_USER}@${TARGET_SERVER}:${DEPLOY_PATH}/
                    '''
                }
            }
        }

        stage('Inject Environment') {
            options { timeout(time: 5, unit: 'MINUTES') }
            steps {
                script { env.CDSS_CURRENT_STAGE = env.STAGE_NAME }
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

        // Repair and verify the currently promoted route before a potentially
        // lengthy build. This also recreates a missing stable router.
        stage('Ensure Live Route') {
            options { timeout(time: 5, unit: 'MINUTES') }
            steps {
                script { env.CDSS_CURRENT_STAGE = env.STAGE_NAME }
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/ensure_live_route.sh deploy/promote_stack.sh \
                                deploy/render_router_config.sh
                            PUBLIC_APP_PORT=${APP_PORT} ./deploy/ensure_live_route.sh
                        "
                    '''
                }
            }
        }

        // Build both application images once and in parallel after the new
        // source and production environment have reached the target host.
        // Provision and promotion reuse these exact images.
        stage('Build Images') {
            options { timeout(time: 30, unit: 'MINUTES') }
            steps {
                script { env.CDSS_CURRENT_STAGE = env.STAGE_NAME }
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
            options { timeout(time: 20, unit: 'MINUTES') }
            steps {
                script { env.CDSS_CURRENT_STAGE = env.STAGE_NAME }
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

        // Stop new mutating requests and wait for the old router workers to
        // drain before pg_dump takes the candidate database snapshot.
        stage('Enable Write Lock') {
            options { timeout(time: 5, unit: 'MINUTES') }
            steps {
                script { env.CDSS_CURRENT_STAGE = env.STAGE_NAME }
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/set_write_lock.sh deploy/promote_stack.sh \
                                deploy/render_router_config.sh
                            PUBLIC_APP_PORT=${APP_PORT} ./deploy/set_write_lock.sh enable
                        "
                    '''
                }
            }
        }

        // Creates an isolated database volume, clones the live database into
        // it, then migrates and seeds it without changing tree_layouts.
        // Production remains online throughout this stage.
        stage('Provision New Stack') {
            options { timeout(time: 35, unit: 'MINUTES') }
            steps {
                script { env.CDSS_CURRENT_STAGE = env.STAGE_NAME }
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
            options { timeout(time: 10, unit: 'MINUTES') }
            steps {
                script { env.CDSS_CURRENT_STAGE = env.STAGE_NAME }
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/promote_stack.sh deploy/render_router_config.sh
                            DEPLOY_GIT_COMMIT=${GIT_COMMIT} \
                                PUBLIC_APP_PORT=${APP_PORT} \
                                ./deploy/promote_stack.sh ${VERSION}
                        "
                    '''
                }
            }
        }

        stage('Verify Public Endpoint') {
            options { timeout(time: 5, unit: 'MINUTES') }
            steps {
                script { env.CDSS_CURRENT_STAGE = env.STAGE_NAME }
                sh '''
                    for attempt in $(seq 1 10); do
                        release_header=$(
                            curl -fsS --max-time 10 \
                                -H 'Cache-Control: no-cache' \
                                -D - -o /dev/null \
                                "${PUBLIC_URL}/?deployment_check=${VERSION}" \
                                | tr -d '\\r' \
                                | awk 'tolower($1) == "x-cdss-release:" { print $2 }' \
                                | tail -n 1 \
                                || true
                        )
                        if [ "$release_header" = "${VERSION}" ] \
                            && curl -fsS --max-time 10 "${PUBLIC_URL}/health" > /dev/null; then
                            echo "Public endpoint is serving release ${VERSION}."
                            exit 0
                        fi
                        echo "Public endpoint attempt ${attempt} failed (release header: ${release_header:-none})."
                        sleep 2
                    done
                    echo "ERROR: ${PUBLIC_URL} did not serve healthy release ${VERSION}." >&2
                    exit 1
                '''
            }
        }

        // Writes resume only after the promoted release is externally
        // reachable and identifies itself as this exact build.
        stage('Disable Write Lock') {
            options { timeout(time: 5, unit: 'MINUTES') }
            steps {
                script { env.CDSS_CURRENT_STAGE = env.STAGE_NAME }
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/set_write_lock.sh deploy/promote_stack.sh \
                                deploy/render_router_config.sh
                            PUBLIC_APP_PORT=${APP_PORT} ./deploy/set_write_lock.sh disable
                        "
                    '''
                }
            }
        }

        // Retain the previous application stack until the new release has
        // passed both host-local and public verification and writes resumed.
        stage('Prune Old Stacks') {
            options { timeout(time: 10, unit: 'MINUTES') }
            steps {
                script { env.CDSS_CURRENT_STAGE = env.STAGE_NAME }
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                            set -e
                            cd ${DEPLOY_PATH}
                            chmod +x deploy/prune_old_stacks.sh
                            PUBLIC_APP_PORT=${APP_PORT} ./deploy/prune_old_stacks.sh
                        "
                    '''
                }
            }
        }

        stage('Record Deployment Evidence') {
            options { timeout(time: 5, unit: 'MINUTES') }
            steps {
                script { env.CDSS_CURRENT_STAGE = env.STAGE_NAME }
                sshagent(['ubuntu-vm-jenkins']) {
                    sh '''
                        mkdir -p .ci-reports/deployment
                        scp ${SSH_OPTS} \
                            ${TARGET_USER}@${TARGET_SERVER}:${DEPLOY_PATH}/deploy/.deployment_state \
                            .ci-reports/deployment/state.txt
                        {
                            printf 'jenkins_build=%s\n' '${BUILD_NUMBER}'
                            printf 'git_commit=%s\n' '${GIT_COMMIT}'
                            printf 'build_url=%s\n' '${BUILD_URL}'
                            printf 'public_url=%s\n' '${PUBLIC_URL}'
                        } > .ci-reports/deployment/build.txt
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
                        chmod +x deploy/cleanup_failed_stack.sh deploy/promote_stack.sh \
                            deploy/render_router_config.sh deploy/set_write_lock.sh
                        if PUBLIC_APP_PORT=${APP_PORT} \
                            ./deploy/cleanup_failed_stack.sh ${VERSION}; then
                            PUBLIC_APP_PORT=${APP_PORT} ./deploy/set_write_lock.sh disable \
                                || echo 'WARNING: write lock remains enabled because a healthy route could not be verified.'
                        else
                            echo 'WARNING: recovery failed; preserving the write lock and release stacks for diagnosis.'
                        fi
                    "
                '''
            }
        }

        aborted {
            echo 'Deployment aborted - restoring a verified route and write-lock state.'
            sshagent(['ubuntu-vm-jenkins']) {
                sh '''
                    ssh ${SSH_OPTS} ${TARGET_USER}@${TARGET_SERVER} "
                        cd ${DEPLOY_PATH} 2>/dev/null || exit 0
                        chmod +x deploy/cleanup_failed_stack.sh deploy/promote_stack.sh \
                            deploy/render_router_config.sh deploy/set_write_lock.sh
                        if PUBLIC_APP_PORT=${APP_PORT} \
                            ./deploy/cleanup_failed_stack.sh ${VERSION}; then
                            PUBLIC_APP_PORT=${APP_PORT} ./deploy/set_write_lock.sh disable \
                                || echo 'WARNING: write lock remains enabled because a healthy route could not be verified.'
                        else
                            echo 'WARNING: recovery failed; preserving the write lock and release stacks for diagnosis.'
                        fi
                    "
                '''
            }
        }

        cleanup {
            script {
                try {
                    archiveArtifacts(
                        artifacts: '.ci-reports/**/*,frontend/.ci-reports/**/*',
                        allowEmptyArchive: true,
                        fingerprint: false
                    )
                } catch (archiveError) {
                    echo "WARNING: unable to archive CI/CD reports: ${archiveError}"
                }
                // Notification/reporting must never replace the real build
                // result or prevent cleanWs() from running.
                try {
                    def stageNames = [
                        'Checkout',
                        'Verify Files',
                        'Quality Gates',
                        'Deploy Files',
                        'Inject Environment',
                        'Ensure Live Route',
                        'Build Images',
                        'Backup Current Database',
                        'Enable Write Lock',
                        'Provision New Stack',
                        'Promote New Stack',
                        'Verify Public Endpoint',
                        'Disable Write Lock',
                        'Prune Old Stacks',
                        'Record Deployment Evidence'
                    ]
                    def buildResult = currentBuild.currentResult ?: 'UNKNOWN'
                    def activeStage = env.CDSS_CURRENT_STAGE ?: 'Pipeline initialization'
                    def activeStageIndex = stageNames.indexOf(activeStage)
                    def stageRows = ''
                    for (int index = 0; index < stageNames.size(); index++) {
                        def stageName = stageNames[index]
                        def stageResult
                        if (buildResult == 'SUCCESS') {
                            stageResult = 'SUCCESS'
                        } else if (activeStageIndex < 0) {
                            stageResult = 'NOT RUN'
                        } else if (index < activeStageIndex) {
                            stageResult = 'SUCCESS'
                        } else if (index == activeStageIndex) {
                            stageResult = buildResult
                        } else {
                            stageResult = 'NOT RUN'
                        }

                        def color = stageResult == 'SUCCESS'
                            ? '#15803d'
                            : (stageResult == 'NOT RUN' ? '#64748b' : '#b91c1c')
                        stageRows += """
                            <tr>
                                <td style="padding:6px 10px;border:1px solid #cbd5e1;">${stageName}</td>
                                <td style="padding:6px 10px;border:1px solid #cbd5e1;color:${color};font-weight:700;">${stageResult}</td>
                            </tr>
                        """
                    }

                    def commitSummary = sh(
                        script: "git log -1 --pretty=format:'%h %s' 2>/dev/null || true",
                        returnStdout: true
                    ).trim()
                    def resultColor = buildResult == 'SUCCESS' ? '#15803d' : '#b91c1c'
                    def subject = "[CDSS] ${buildResult}: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
                    def configuredRecipients = env.CDSS_NOTIFICATION_EMAILS?.trim()
                    def parameterRecipients = params.NOTIFICATION_EMAILS?.trim()
                    def recipients = configuredRecipients ?: parameterRecipients ?: ''
                    def emailBody = """
                    <html>
                    <body style="font-family:Arial,sans-serif;color:#0f172a;">
                        <h2 style="color:${resultColor};">CDSS build ${buildResult}</h2>
                        <table style="border-collapse:collapse;margin-bottom:18px;">
                            <tr><td><strong>Job</strong></td><td style="padding-left:14px;">${env.JOB_NAME}</td></tr>
                            <tr><td><strong>Build</strong></td><td style="padding-left:14px;">#${env.BUILD_NUMBER}</td></tr>
                            <tr><td><strong>Result</strong></td><td style="padding-left:14px;color:${resultColor};font-weight:700;">${buildResult}</td></tr>
                            <tr><td><strong>Failed/current stage</strong></td><td style="padding-left:14px;">${activeStage}</td></tr>
                            <tr><td><strong>Duration</strong></td><td style="padding-left:14px;">${currentBuild.durationString}</td></tr>
                            <tr><td><strong>Commit</strong></td><td style="padding-left:14px;">${commitSummary ?: 'Unavailable'}</td></tr>
                            <tr><td><strong>Build URL</strong></td><td style="padding-left:14px;"><a href="${env.BUILD_URL}">${env.BUILD_URL}</a></td></tr>
                            <tr><td><strong>Console log</strong></td><td style="padding-left:14px;"><a href="${env.BUILD_URL}console">${env.BUILD_URL}console</a></td></tr>
                        </table>

                        <h3>Stage summary</h3>
                        <table style="border-collapse:collapse;">
                            <thead>
                                <tr>
                                    <th style="padding:6px 10px;border:1px solid #cbd5e1;text-align:left;">Stage</th>
                                    <th style="padding:6px 10px;border:1px solid #cbd5e1;text-align:left;">Status</th>
                                </tr>
                            </thead>
                            <tbody>${stageRows}</tbody>
                        </table>

                        <h3>Final console output (last 150 lines)</h3>
                        <pre style="white-space:pre-wrap;background:#0f172a;color:#e2e8f0;padding:14px;border-radius:6px;">\${BUILD_LOG, maxLines=150, escapeHtml=true}</pre>
                        <p>The complete compressed console log is attached.</p>
                    </body>
                    </html>
                    """

                    emailext(
                            subject: subject,
                            body: emailBody,
                            mimeType: 'text/html',
                            to: recipients,
                            recipientProviders: [
                                developers(),
                                culprits(),
                                requestor()
                            ],
                            attachLog: true,
                            compressLog: true
                        )
                    echo "Build notification email requested for ${recipients ?: 'Jenkins-derived recipients'}."
                } catch (notificationError) {
                    echo "WARNING: unable to prepare or send build notification email: ${notificationError}"
                    echo 'The build result is preserved. Verify the Email Extension plugin and SMTP settings.'
                }
            }
            cleanWs()
        }
    }
}
