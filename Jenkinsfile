pipeline {
    agent any

    environment {
        EC2_HOST    = '54.144.194.189' // Your EC2 IP
        SSH_USER    = 'ubuntu'         // Your SSH user
        SSH_CRED_ID = 'e3057e9e-d907-42db-881f-b8f699c8f692' // Your credential ID
        AWS_REGION  = 'us-east-1'
        // Replace this with your actual ELB DNS or static IP after deployment
        APP_ENDPOINT = 'YOUR_ELB_DNS_OR_IP'
        MYSQL_NS    = 'database'
        APP_NS      = 'application'
        TIMEOUT     = '300' // 5 minutes timeout in seconds
    }

    options {
        timeout(time: 45, unit: 'MINUTES') // Global pipeline timeout
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
                timeout(time: 5, unit: 'MINUTES') {
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
        }

        stage('Install eksctl on EC2') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
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
        }

        stage('Check IAM Role on EC2') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
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
        }

        stage('Create EKS Cluster') {
            steps {
                timeout(time: 25, unit: 'MINUTES') {  // Increased timeout for cluster creation
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

                                echo "Creating namespaces..."
                                kubectl create namespace ${env.MYSQL_NS} --dry-run=client -o yaml | kubectl apply -f -
                                kubectl create namespace ${env.APP_NS} --dry-run=client -o yaml | kubectl apply -f -

                                echo "Checking for default StorageClass..."
                                kubectl get storageclass
                                SC_DEFAULT=\$(kubectl get storageclass -o jsonpath="{.items[?(@.metadata.annotations.storageclass\\.kubernetes\\.io/is-default-class=='true')].metadata.name}")
                                if [ -z "\$SC_DEFAULT" ]; then
                                    echo "Warning: No default StorageClass found"
                                else
                                    echo "Default StorageClass is: \$SC_DEFAULT"
                                fi

                                echo "If you see credential errors, ensure the EC2 instance has an appropriate IAM role attached."
                            '
                        """
                    }
                }
            }
        }

        stage('Install MySQL Database') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    sshagent([env.SSH_CRED_ID]) {
                        sh """
                            echo "=== Installing MySQL Database ==="
                            ssh -o StrictHostKeyChecking=no ${env.SSH_USER}@${env.EC2_HOST} '
                                cd ~
                                # Clone the repository if not already cloned
                                if [ ! -d "AWS_APP" ]; then
                                    git clone https://github.com/Ben-levi/AWS_APP.git
                                else
                                    cd AWS_APP && git pull && cd ~
                                fi

                                # Check if MySQL PVC exists first
                                echo "Checking for MySQL PVC..."
                                if kubectl get pvc mysql-pvc -n ${env.MYSQL_NS} 2>/dev/null; then
                                    echo "MySQL PVC exists"
                                    kubectl describe pvc mysql-pvc -n ${env.MYSQL_NS}
                                else
                                    echo "Creating MySQL PVC..."
                                    kubectl apply -f AWS_APP/k8s/DB/mysql-pvc.yaml -n ${env.MYSQL_NS}
                                    echo "Waiting for PVC to be bound..."
                                    kubectl wait --for=condition=bound pvc/mysql-pvc -n ${env.MYSQL_NS} --timeout=60s || echo "PVC not bound within timeout"
                                    kubectl describe pvc mysql-pvc -n ${env.MYSQL_NS}
                                fi
                                
                                # Check if MySQL configmap exists
                                echo "Checking for MySQL ConfigMap..."
                                if ! kubectl get configmap mysql-configmap -n ${env.MYSQL_NS} 2>/dev/null; then
                                    echo "Creating MySQL ConfigMap..."
                                    kubectl apply -f AWS_APP/k8s/DB/MySQL_ConfigMap -n ${env.MYSQL_NS}
                                fi

                                # Check if MySQL deployment exists
                                if kubectl get deployment -n ${env.MYSQL_NS} | grep -q "mysql"; then
                                    echo "MySQL deployment already exists."
                                    kubectl get pods -l app=mysql -n ${env.MYSQL_NS}
                                    kubectl describe pod -l app=mysql -n ${env.MYSQL_NS} | grep -A 10 "Events:"
                                else
                                    echo "Installing MySQL deployment..."
                                    kubectl apply -f AWS_APP/k8s/DB/mysql-deployment-svc.yaml -n ${env.MYSQL_NS}
                                fi

                                # Create PHPMyAdmin if needed
                                if ! kubectl get deployment -n ${env.MYSQL_NS} | grep -q "phpmyadmin"; then
                                    echo "Installing PHPMyAdmin..."
                                    kubectl apply -f AWS_APP/k8s/DB/phpmyadmin-deployment-svc.yaml -n ${env.MYSQL_NS}
                                fi
                                
                                # Check if MySQL pod is running
                                echo "Checking MySQL pod status..."
                                POD_STATUS=\$(kubectl get pods -l app=mysql -n ${env.MYSQL_NS} -o jsonpath="{.items[0].status.phase}" 2>/dev/null || echo "NotFound")
                                echo "MySQL pod status: \$POD_STATUS"
                                
                                if [ "\$POD_STATUS" != "Running" ]; then
                                    echo "MySQL pod is not running. Checking logs..."
                                    POD_NAME=\$(kubectl get pods -l app=mysql -n ${env.MYSQL_NS} -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
                                    if [ -n "\$POD_NAME" ]; then
                                        kubectl logs \$POD_NAME -n ${env.MYSQL_NS}
                                        kubectl describe pod \$POD_NAME -n ${env.MYSQL_NS}
                                    fi
                                else
                                    echo "MySQL pod is running"
                                fi

                                # Verify MySQL service
                                echo "Verifying MySQL service..."
                                kubectl get svc mysql-service -n ${env.MYSQL_NS}
                                
                                # Check if MySQL is accessible inside the cluster
                                echo "Testing MySQL connectivity from inside the cluster..."
                                cat <<EOF | kubectl apply -f -
                                apiVersion: v1
                                kind: Pod
                                metadata:
                                  name: mysql-test-client
                                  namespace: ${env.MYSQL_NS}
                                spec:
                                  containers:
                                  - name: mysql-client
                                    image: mysql:8.0
                                    command: ["sleep", "60"]
                                  restartPolicy: Never
                                EOF
                                
                                # Wait for the test pod to be ready
                                kubectl wait --for=condition=ready pod/mysql-test-client -n ${env.MYSQL_NS} --timeout=30s || echo "Test pod not ready within timeout"
                                
                                # Test connectivity
                                echo "Attempting to connect to MySQL from test pod..."
                                kubectl exec -n ${env.MYSQL_NS} mysql-test-client -- \
                                  mysql -h mysql-service -uroot -padmin -e "SHOW DATABASES;" || \
                                  echo "MySQL connection test failed"
                                
                                # Clean up test pod
                                kubectl delete pod mysql-test-client -n ${env.MYSQL_NS} --wait=false
                            '
                        """
                    }
                }
            }
        }

        stage('Deploy Application to EKS') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    sshagent([env.SSH_CRED_ID]) {
                        sh """
                            echo "=== Deploying Application to EKS ==="
                            ssh -o StrictHostKeyChecking=no ${env.SSH_USER}@${env.EC2_HOST} '
                                cd ~
                                # Repository should be cloned in the previous step
                                cd AWS_APP/k8s
                                
                                # Set the database connection environment variables in configmap
                                echo "Updating application ConfigMap with database connection..."
                                cat <<EOF > db-configmap-patch.yaml
                                data:
                                  DB_HOST: "mysql-service.${env.MYSQL_NS}.svc.cluster.local"
                                  DB_USER: "root"
                                  DB_PASSWORD: "admin"
                                  DB_PORT: "3306"
                                  DB_NAME: "tasks_app"
                                EOF
                                
                                # Apply ConfigMap and Secret
                                echo "Applying ConfigMap and Secret..."
                                if kubectl get configmap app-config -n ${env.APP_NS} 2>/dev/null; then
                                    kubectl patch configmap app-config -n ${env.APP_NS} --patch-file db-configmap-patch.yaml
                                else
                                    kubectl apply -f configmap-and-secret.yaml -n ${env.APP_NS}
                                    kubectl patch configmap app-config -n ${env.APP_NS} --patch-file db-configmap-patch.yaml
                                fi
                                
                                # Check if deployment exists and get its name
                                DEPLOYMENT_NAME=\$(kubectl get deployments -n ${env.APP_NS} | grep todo | awk "{print \\\$1}")
                                
                                if [ -n "\$DEPLOYMENT_NAME" ]; then
                                    echo "Application deployment already exists as \$DEPLOYMENT_NAME. Updating..."
                                    kubectl apply -f deployment-and-services.yaml -n ${env.APP_NS}
                                    
                                    # Restart the deployment to pick up the new ConfigMap and Secret
                                    echo "Restarting deployment \$DEPLOYMENT_NAME to apply new configuration..."
                                    kubectl rollout restart deployment/\$DEPLOYMENT_NAME -n ${env.APP_NS}
                                else
                                    echo "Creating new application deployment..."
                                    kubectl apply -f deployment-and-services.yaml -n ${env.APP_NS}
                                fi
                                
                                # Get the actual deployment name after applying
