pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
        disableConcurrentBuilds()
    }

    parameters {
        booleanParam(name: 'PUSH_IMAGE', defaultValue: false,
                     description: 'Push the image to Docker Hub (needs the "dockerhub" credentials)')
    }

    environment {
        IMAGE = 'reteval'
        TEST_IMAGE = 'reteval-test'
    }

    stages {
        stage('Prepare') {
            steps {
                script {
                    env.TAG = env.GIT_COMMIT.take(7)
                }
                sh 'docker version --format "client {{.Client.Version}}, server {{.Server.Version}}"'
            }
        }

        stage('Build test image') {
            steps {
                sh 'docker build --target test -t "$TEST_IMAGE:$TAG" .'
            }
        }

        stage('Static checks') {
            parallel {
                stage('Ruff') {
                    steps {
                        sh 'docker run --rm "$TEST_IMAGE:$TAG" sh -c "ruff check . && ruff format --check ."'
                    }
                }
                stage('Mypy') {
                    steps {
                        sh 'docker run --rm "$TEST_IMAGE:$TAG" mypy'
                    }
                }
            }
        }

        stage('Unit tests') {
            steps {
                sh '''
                    name="reteval-tests-$BUILD_NUMBER"
                    docker rm -f "$name" >/dev/null 2>&1 || true
                    status=0
                    docker run --name "$name" "$TEST_IMAGE:$TAG" \
                        pytest --cov --cov-report=term --cov-report=xml:/tmp/coverage.xml \
                               --junitxml=/tmp/junit.xml || status=$?
                    docker cp "$name:/tmp/junit.xml" junit.xml || true
                    docker cp "$name:/tmp/coverage.xml" coverage.xml || true
                    docker rm -f "$name" >/dev/null
                    exit $status
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'junit.xml'
                    archiveArtifacts artifacts: 'coverage.xml', allowEmptyArchive: true
                }
            }
        }

        stage('Build image') {
            steps {
                sh '''
                    docker build --target runtime \
                        --label "org.opencontainers.image.revision=$GIT_COMMIT" \
                        -t "$IMAGE:$TAG" -t "$IMAGE:latest" .
                    docker run --rm "$IMAGE:$TAG" --version
                '''
            }
        }

        stage('Reproduce example') {
            steps {
                sh 'docker run --rm -i --entrypoint sh "$IMAGE:$TAG" -s < ci/verify_example.sh'
            }
        }

        stage('Push to Docker Hub') {
            when { expression { params.PUSH_IMAGE } }
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub',
                                                  usernameVariable: 'HUB_USER',
                                                  passwordVariable: 'HUB_TOKEN')]) {
                    sh '''
                        export DOCKER_CONFIG="$(mktemp -d)"
                        trap 'rm -rf "$DOCKER_CONFIG"' EXIT
                        echo "$HUB_TOKEN" | docker login -u "$HUB_USER" --password-stdin
                        docker tag "$IMAGE:$TAG" "$HUB_USER/$IMAGE:$TAG"
                        docker tag "$IMAGE:$TAG" "$HUB_USER/$IMAGE:latest"
                        docker push "$HUB_USER/$IMAGE:$TAG"
                        docker push "$HUB_USER/$IMAGE:latest"
                    '''
                }
            }
        }

        stage('Deploy to Kubernetes') {
            when {
                expression { sh(returnStatus: true, script: 'kubectl get nodes >/dev/null 2>&1') == 0 }
            }
            steps {
                sh '''
                    node=$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
                    docker save "$IMAGE:$TAG" | docker exec -i "$node" ctr --namespace=k8s.io images import -
                    kubectl delete job reteval-example --ignore-not-found
                    sed "s|__IMAGE__|$IMAGE:$TAG|" k8s/job.yaml | kubectl apply -f -
                    kubectl wait --for=condition=complete job/reteval-example --timeout=120s
                    kubectl logs job/reteval-example | diff -u examples/expected/report.md -
                    kubectl get job reteval-example
                '''
            }
        }
    }

    post {
        always {
            sh 'docker image prune -f >/dev/null || true'
        }
    }
}
