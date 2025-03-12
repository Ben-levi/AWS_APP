pipeline {
    agent any

    environment {
        EC2_HOST    = '54.144.194.189' // Your EC2 IP
        SSH_USER    = 'ubuntu'         // Your SSH user
        SSH_CRED_ID = 'e3057e9e-d907-42db-881f-b8f699c8f692' // Your credential ID
        AWS_REGION  = 'us-east-1'
        // Replace this with your actual ELB DNS or static IP after deployment
        APP_ENDPOINT = 'YOUR_ELB_DNS_OR_IP'
    }

    stages {
        stage('System Info') {
            steps {
                sh '''
                    echo "=== System Information ==="
                    echo "Host: $(hostname)"
                    echo "User: $(whoami)"
                    echo "Working directory: $(pwd)"
                '''
            }
        }

        stage('Test SSH Connection') {
            steps {
                sshagent([env.SSH_CRED_ID]) {
                    sh """
                        echo "=== SSH Connectivity Check ==="
                        ssh -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=10 ${env.SSH_USER}@${env.EC2_HOST} \\
                        'echo "SSH connection successful"; uname -a; uptime; df -h; free -m' \\
                        || echo "SSH connection failed. Check your SSH key and security group settings."
                    """
                }
            }
        }

        stage('Install eksctl on EC2') {
            steps {
                sshagent([env.SSH_CRED_ID]) {
                    sh """
                        echo "=== Installing eksctl on EC2 instance ==="
                        ssh -o StrictHostKeyChecking=no ${env.SSH_USER}@${env.EC2_HOST} '
                            if ! command -v eksctl &> /dev/null; then
                                echo "eksctl not found, installing..."
                                mkdir -p ~/tmp
                                curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_\$(uname -s)_amd64.tar.gz" | tar xz -C ~/tmp
                                sudo mv ~/tmp/eksctl /usr/local/bin/
                                rm -rf ~/tmp
                                eksctl version
                            else
                                echo "eksctl is already installed"
                                eksctl version
                            fi
                        '
                    """
                }
            }
        }

        stage('Check IAM Role on EC2') {
            steps {
                sshagent([env.SSH_CRED_ID]) {
                    sh """
                        echo "=== Checking IAM Role on EC2 instance ==="
                        ssh -o StrictHostKeyChecking=no ${env.SSH_USER}@${env.EC2_HOST} '
                            ROLE_INFO=\$(curl -s http://169.254.169.254/latest/meta-data/iam/info || echo "No IAM role found")
                            echo "IAM Role info: \$ROLE_INFO"
                            if [[ "\$ROLE_INFO" == *"No IAM role found"* ]]; then
                                echo "Warning: No IAM role attached to this instance. Please attach an IAM role with the following policies:"
                                echo " - AmazonEKSClusterPolicy"
                                echo " - AmazonEKSWorkerNodePolicy"
                                echo " - AmazonEC2ContainerRegistryReadOnly"
                                exit 1
                            fi
                        '
                    """
                }
            }
        }

        stage('Create EKS Cluster') {
            steps {
                sshagent([env.SSH_CRED_ID]) {
                    sh """
                        echo "=== Creating EKS Cluster ==="
                        ssh -o StrictHostKeyChecking=no ${env.SSH_USER}@${env.EC2_HOST} '
                            # Install AWS CLI v2 if not found
                            if ! command -v aws &> /dev/null; then
                                echo "AWS CLI not found, installing..."
                                sudo apt-get update && sudo apt-get install -y unzip
                                curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
                                unzip awscliv2.zip
                                sudo ./aws/install
                                rm -rf awscliv2.zip aws
                            fi

                            # Install kubectl if not found
                            if ! command -v kubectl &> /dev/null; then
                                echo "kubectl not found, installing..."
                                curl -LO "https://dl.k8s.io/release/\$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
                                chmod +x kubectl
                                sudo mv kubectl /usr/local/bin/
                                kubectl version --client
                            fi

                            # Check if the EKS cluster already exists using AWS CLI
                            if aws eks describe-cluster --name my-eks-cluster --region ${env.AWS_REGION} > /dev/null 2>&1; then
                                echo "EKS cluster my-eks-cluster already exists. Using existing cluster."
                            else
                                echo "EKS cluster not found. Creating new EKS cluster. This may take 15-20 minutes..."
                                eksctl create cluster \\
                                  --name my-eks-cluster \\
                                  --region ${env.AWS_REGION} \\
                                  --nodegroup-name my-nodes \\
                                  --node-type t3.medium \\
                                  --nodes 2 \\
                                  --managed
                            fi

                            echo "Verifying EKS cluster..."
                            eksctl get cluster --name my-eks-cluster --region ${env.AWS_REGION}

                            echo "Configuring kubectl..."
                            aws eks update-kubeconfig --name my-eks-cluster --region ${env.AWS_REGION}

                            echo "Checking Kubernetes nodes..."
                            kubectl get nodes

                            echo "If you see credential errors, ensure the EC2 instance has an appropriate IAM role attached."
                        '
                    """
                }
            }
        }

        stage('Deploy Application to EKS') {
            steps {
                sshagent([env.SSH_CRED_ID]) {
                    sh """
                        echo "=== Deploying Application to EKS ==="
                        ssh -o StrictHostKeyChecking=no ${env.SSH_USER}@${env.EC2_HOST} '
                            cd ~
                            # Remove any previous clone and clone the repository afresh
                            rm -rf AWS_APP
                            git clone https://github.com/Ben-levi/AWS_APP.git
                            cd AWS_APP/k8s
                            echo "Applying ConfigMap and Secret..."
                            kubectl apply -f configmap-and-secret.yaml
                            echo "Applying Deployment and Internal Service..."
                            kubectl apply -f deployment-and-services.yaml
                            echo "Applying ELB Service..."
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
                        echo "=== Checking Kubernetes Resources on EKS ==="
                        ssh -o StrictHostKeyChecking=no ${env.SSH_USER}@${env.EC2_HOST} '
                            echo "Listing all pods:"
                            kubectl get pods -o wide
                            echo "Listing services:"
                            kubectl get svc -o wide
                            echo "Describing contacts-service (ELB):"
                            kubectl describe svc contacts-service
                            echo "Listing events:"
                            kubectl get events --sort-by=.metadata.creationTimestamp
                        '
                    """
                }
            }
        }

        stage('Test Application via ELB') {
            steps {
                // Wait for the ELB to be provisioned and DNS to propagate
                sh 'sleep 60'
                echo "=== Testing Application via ELB ==="
                sh 'curl -s http://${APP_ENDPOINT}:5053 || echo "Application not reachable via ELB"'
            }
        }
    }

    post {
        always {
            echo "==== Pipeline execution completed ===="
        }
        success {
            echo "✅ Successfully installed eksctl, verified IAM role, created/used existing EKS cluster, deployed application with ELB, and checked deployment status"
        }
        failure {
            echo "❌ Pipeline failed, see logs for details"
        }
    }
}
