pipeline {
    agent any

    environment {
        EC2_HOST    = '54.144.194.189' // Your EC2 IP
        SSH_USER    = 'ubuntu'         // Your SSH user
        SSH_CRED_ID = 'e3057e9e-d907-42db-881f-b8f699c8f692' // Your credential ID
        AWS_REGION  = 'us-east-1'
        DOCKER_IMAGE = 'benl89/todo_app'
        DOCKER_TAG = 'latest'
        DB_HOST = 'mysql'  // Database host for the app
    }

    stages {
        stage('System Info') {
            steps {
                sh 'echo "=== System Information ==="'
                sh 'hostname'
                sh 'whoami'
                sh 'pwd'
            }
        }

        stage('Checkout Code') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'git_pass')]) {
                    sh 'git clone https://github.com/Ben-levi/AWS_APP.git'
                }
            }
        }

        stage('Verify Files') {
            steps {
                sh '''
                    echo "Workspace contents:"
                    ls -la
                    echo "Contents of requirements.txt (if present):"
                    if [ -f requirements.txt ]; then
                        cat requirements.txt
                    else
                        echo "requirements.txt not found"
                        exit 1
                    fi
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh """
                    echo "Building Docker image..."
                    docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} --build-arg DB_HOST=${DB_HOST} .
                """
            }
        }

        stage('Login to DockerHub') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-credentials', passwordVariable: 'DOCKERHUB_PASSWORD', usernameVariable: 'DOCKERHUB_USERNAME')]) {
                    sh 'docker login -u $DOCKERHUB_USERNAME -p $DOCKERHUB_PASSWORD'
                }
            }
        }

        stage('Push to DockerHub') {
            steps {
                sh "docker push ${DOCKER_IMAGE}:${DOCKER_TAG}"
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                sshagent([env.SSH_CRED_ID]) {
                    sh """
                        echo "=== Deploying Application to EKS ==="
                        ssh -o StrictHostKeyChecking=no ${env.SSH_USER}@${env.EC2_HOST} '
                            cd ~
                            rm -rf AWS_APP
                            git clone https://github.com/Ben-levi/AWS_APP.git
                            cd AWS_APP/k8s
                            kubectl apply -f configmap-and-secret.yaml
                            kubectl apply -f deployment-and-services.yaml
                            kubectl apply -f service-elb.yaml
                        '
                    """
                }
            }
        }

        stage('Check Deployment Status') {
            steps {
                sshagent([env.SSH_CRED_ID]) {
                    sh """
                        ssh -o StrictHostKeyChecking=no ${env.SSH_USER}@${env.EC2_HOST} '
                            kubectl get pods -o wide
                            kubectl get svc -o wide
                            kubectl describe svc contacts-service
                        '
                    """
                }
            }
        }

        stage('Test Application via ELB') {
            steps {
                sh 'sleep 60'
                sh 'curl -s http://${APP_ENDPOINT}:5053 || echo "Application not reachable via ELB"'
            }
        }
    }

    post {
        always {
            sh 'docker logout'
            sh "docker rmi ${DOCKER_IMAGE}:${DOCKER_TAG} || exit 0"
        }
        success {
            echo "✅ Successfully deployed application and tested ELB"
        }
        failure {
            echo "❌ Deployment failed, check logs for details"
        }
    }
}
