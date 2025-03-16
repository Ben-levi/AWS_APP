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
    }

    options {
        // Add timeout for the entire pipeline - use direct value instead of env variable
        timeout(time: 5, unit: 'MINUTES')
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
            options {
                timeout(time: 5, unit: 'MINUTES')
            }
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

                            # Verify storage classes available in the cluster
                            echo "=== Checking available StorageClasses ==="
                            kubectl get storageclass
                            echo "Checking if standard StorageClass exists:"
                            kubectl get storageclass standard || echo "StorageClass \"standard\" not found"
                            
                            echo "Creating namespaces..."
                            kubectl create namespace ${env.MYSQL_NS} --dry-run=client -o yaml | kubectl apply -f -
                            kubectl create namespace ${env.APP_NS} --dry-run=client -o yaml | kubectl apply -f -

                            echo "If you see credential errors, ensure the EC2 instance has an appropriate IAM role attached."
                        '
                    """
                }
            }
        }

        stage('Install MySQL Database') {
            options {
                timeout(time: 5, unit: 'MINUTES')
            }
            steps {
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

                            # Check if StorageClass exists (needed for MySQL PVC)
                            echo "=== Verifying StorageClass for MySQL PVC ==="
                            if ! kubectl get storageclass | grep -q "standard"; then
                                echo "WARNING: StorageClass \"standard\" not found. Creating default gp2 StorageClass and marking as default..."
                                cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp2
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
EOF
                            fi

                            # Check if MySQL PVC exists before deployment
                            echo "=== Checking existing MySQL PVC ==="
                            kubectl get pvc -n ${env.MYSQL_NS} || echo "No PVCs found in ${env.MYSQL_NS} namespace"

                            # Check if MySQL deployment exists
                            if kubectl get deployment -n ${env.MYSQL_NS} | grep -q "mysql"; then
                                echo "MySQL deployment already exists. Checking status..."
                                kubectl get pods -n ${env.MYSQL_NS} -l app=mysql -o wide
                                kubectl describe pods -n ${env.MYSQL_NS} -l app=mysql | grep -A5 "State:"
                            else
                                echo "Installing MySQL from the repo..."
                                # Apply MySQL ConfigMap first
                                kubectl apply -f AWS_APP/k8s/DB/MySQL_ConfigMap -n ${env.MYSQL_NS}
                                
                                # Apply PVC before deployment
                                echo "Creating MySQL PVC..."
                                kubectl apply -f AWS_APP/k8s/DB/mysql-pvc.yaml -n ${env.MYSQL_NS}
                                
                                # Verify PVC status before proceeding
                                echo "Checking PVC status:"
                                kubectl get pvc -n ${env.MYSQL_NS}
                                kubectl describe pvc -n ${env.MYSQL_NS}
                                
                                # Apply MySQL deployment and service
                                echo "Deploying MySQL..."
                                kubectl apply -f AWS_APP/k8s/DB/mysql-deployment-svc.yaml -n ${env.MYSQL_NS}
                                
                                # Apply phpMyAdmin
                                kubectl apply -f AWS_APP/k8s/DB/phpmyadmin-deployment-svc.yaml -n ${env.MYSQL_NS}
                                
                                # Wait for MySQL to be ready
                                echo "Waiting for MySQL to be ready..."
                                kubectl wait --for=condition=available deployment -l app=mysql -n ${env.MYSQL_NS} --timeout=300s || echo "Timeout waiting for MySQL deployment"
                            fi

                            # Verify MySQL deployment details
                            echo "=== MySQL Deployment Status ==="
                            kubectl get pods -n ${env.MYSQL_NS} -o wide
                            kubectl get pvc -n ${env.MYSQL_NS}
                            kubectl get pv
                            kubectl describe pods -n ${env.MYSQL_NS} -l app=mysql | grep -A10 "Events:"
                            
                            # Check MySQL logs
                            echo "=== MySQL Container Logs ==="
                            MYSQL_POD=\$(kubectl get pods -n ${env.MYSQL_NS} -l app=mysql -o jsonpath="{.items[0].metadata.name}" 2>/dev/null) || echo "No MySQL pods found"
                            if [ -n "\$MYSQL_POD" ]; then
                                kubectl logs \$MYSQL_POD -n ${env.MYSQL_NS} --tail=20
                                
                                # Test MySQL connectivity from within the pod
                                echo "=== Testing MySQL connectivity from within pod ==="
                                kubectl exec -it \$MYSQL_POD -n ${env.MYSQL_NS} -- mysql -u root -ppassword -e "SHOW DATABASES;" || echo "Failed to connect to MySQL"
                            fi
                            
                            echo "=== MySQL Services ==="
                            kubectl get svc -n ${env.MYSQL_NS}
                        '
                    """
                }
            }
        }

        stage('Deploy Application to EKS') {
            options {
                timeout(time: 5, unit: 'MINUTES')
            }
            steps {
                sshagent([env.SSH_CRED_ID]) {
                    sh """
                        echo "=== Deploying Application to EKS ==="
                        ssh -o StrictHostKeyChecking=no ${env.SSH_USER}@${env.EC2_HOST} '
                            cd ~
                            # Repository should be cloned in the previous step
                            cd AWS_APP/k8s
                            
                            # Apply ConfigMap and Secret
                            echo "Applying ConfigMap and Secret..."
                            kubectl apply -f configmap-and-secret.yaml -n ${env.APP_NS}
                            
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
                            DEPLOYMENT_NAME=\$(kubectl get deployments -n ${env.APP_NS} | grep todo | awk "{print \\\$1}")
                            echo "Deployment name is: \$DEPLOYMENT_NAME"
                            
                            # Apply the ELB service
                            echo "Applying ELB service..."
                            kubectl apply -f service-elb.yaml -n ${env.APP_NS}
                            
                            # Get the ELB service name
                            ELB_SVC_NAME=\$(kubectl get svc -n ${env.APP_NS} | grep -E "todo|LoadBalancer" | awk "{print \\\$1}")
                            echo "ELB service name is: \$ELB_SVC_NAME"
                            
                            # Increase the timeout for application to be ready
                            echo "Waiting for application to be ready..."
                            kubectl wait --for=condition=available deployment/\$DEPLOYMENT_NAME -n ${env.APP_NS} --timeout=300s || echo "Timeout waiting for application deployment"
                            
                            # Check logs for MySQL connection issues
                            APP_POD=\$(kubectl get pods -n ${env.APP_NS} -l app=todo-app -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
                            if [ -n "\$APP_POD" ]; then
                                echo "=== Application Pod Logs (check for MySQL connection issues) ==="
                                kubectl logs \$APP_POD -n ${env.APP_NS}
                            fi
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
                            echo "Listing all pods in application namespace:"
                            kubectl get pods -n ${env.APP_NS} -o wide
                            
                            echo "Listing all pods in database namespace:"
                            kubectl get pods -n ${env.MYSQL_NS} -o wide
                            
                            echo "Listing services in application namespace:"
                            kubectl get svc -n ${env.APP_NS} -o wide
                            
                            echo "Listing services in database namespace:"
                            kubectl get svc -n ${env.MYSQL_NS} -o wide
                            
                            # Check Persistent Volumes and Claims
                            echo "=== PersistentVolume Status ==="
                            kubectl get pv
                            
                            echo "=== PersistentVolumeClaim Status ==="
                            kubectl get pvc -n ${env.MYSQL_NS}
                            kubectl describe pvc -n ${env.MYSQL_NS}
                            
                            # Check application to MySQL connectivity
                            echo "=== Testing MySQL Connectivity from Application ==="
                            APP_POD=\$(kubectl get pods -n ${env.APP_NS} -l app=todo-app -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
                            if [ -n "\$APP_POD" ]; then
                                echo "Testing network connectivity from \$APP_POD to MySQL service:"
                                kubectl exec -it \$APP_POD -n ${env.APP_NS} -- bash -c "nc -zvw3 mysql.${env.MYSQL_NS}.svc.cluster.local 3306" || echo "MySQL connectivity check failed"
                                
                                # Test DNS resolution
                                echo "Testing DNS resolution for MySQL service:"
                                kubectl exec -it \$APP_POD -n ${env.APP_NS} -- bash -c "nslookup mysql.${env.MYSQL_NS}.svc.cluster.local" || echo "DNS resolution failed"
                                
                                # Check environment variables in application pod:"
                                echo "Checking environment variables in application pod:"
                                kubectl exec -it \$APP_POD -n ${env.APP_NS} -- bash -c "env | grep -i -E \'mysql|db|database\'" || echo "No MySQL environment variables found"
                            fi
                            
                            echo "Describing todo-service (ELB):"
                            kubectl describe svc todo-service -n ${env.APP_NS}
                            
                            echo "Retrieving ELB endpoint:"
                            ELB_ENDPOINT=\$(kubectl get svc todo-service -n ${env.APP_NS} -o jsonpath="{.status.loadBalancer.ingress[0].hostname}")
                            echo "ELB Endpoint: \$ELB_ENDPOINT"
                            
                            echo "=== Recent Events ==="
                            kubectl get events -n ${env.APP_NS} --sort-by=.metadata.creationTimestamp | tail -n 20
                            kubectl get events -n ${env.MYSQL_NS} --sort-by=.metadata.creationTimestamp | tail -n 20
                        '
                    """
                }
            }
        }

        stage('Test MySQL Schema') {
            steps {
                sshagent([env.SSH_CRED_ID]) {
                    sh """
                        echo "=== Testing MySQL Database Schema ==="
                        ssh -o StrictHostKeyChecking=no ${env.SSH_USER}@${env.EC2_HOST} '
                            # Find MySQL pod
                            MYSQL_POD=\$(kubectl get pods -n ${env.MYSQL_NS} -l app=mysql -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
                            
                            if [ -n "\$MYSQL_POD" ]; then
                                echo "Checking MySQL databases and tables:"
                                kubectl exec -it \$MYSQL_POD -n ${env.MYSQL_NS} -- mysql -u root -ppassword -e "SHOW DATABASES;"
                                kubectl exec -it \$MYSQL_POD -n ${env.MYSQL_NS} -- mysql -u root -ppassword -e "USE todos; SHOW TABLES;" || echo "Todo database not found or tables not created"
                                
                                # Check if the todos database exists, if not create it
                                echo "Ensuring todos database exists:"
                                kubectl exec -it \$MYSQL_POD -n ${env.MYSQL_NS} -- mysql -u root -ppassword -e "CREATE DATABASE IF NOT EXISTS todos;"
                                
                                # Check if tasks table exists, if not create it
                                echo "Ensuring tasks table exists:"
                                kubectl exec -it \$MYSQL_POD -n ${env.MYSQL_NS} -- mysql -u root -ppassword -e "USE todos; CREATE TABLE IF NOT EXISTS tasks (id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(255) NOT NULL, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
                                
                                # Insert test data
                                echo "Inserting test data:"
                                kubectl exec -it \$MYSQL_POD -n ${env.MYSQL_NS} -- mysql -u root -ppassword -e "USE todos; INSERT INTO tasks (title, description) VALUES (\'Test Task\', \'This is a test task\');"
                                
                                # Check data
                                echo "Checking inserted data:"
                                kubectl exec -it \$MYSQL_POD -n ${env.MYSQL_NS} -- mysql -u root -ppassword -e "USE todos; SELECT * FROM tasks;"
                            else
                                echo "MySQL pod not found"
                            fi
                        '
                    """
                }
            }
        }

        stage('Get ELB Endpoint') {
            steps {
                sshagent([env.SSH_CRED_ID]) {
                    script {
                        def elbEndpoint = sh(
                            script: """
                                ssh -o StrictHostKeyChecking=no ${env.SSH_USER}@${env.EC2_HOST} '
                                    kubectl get svc todo-service -n ${env.APP_NS} -o jsonpath="{.status.loadBalancer.ingress[0].hostname}"
                                '
                            """,
                            returnStdout: true
                        ).trim()
                        
                        if (elbEndpoint) {
                            env.APP_ENDPOINT = elbEndpoint
                            echo "ELB Endpoint detected: ${env.APP_ENDPOINT}"
                        } else {
                            echo "ELB Endpoint not available yet"
                        }
                    }
                }
            }
        }

        stage('Test Application via ELB') {
            steps {
                // Wait for the ELB to be provisioned and DNS to propagate
                sh 'sleep 30'
                echo "=== Testing Application via ELB ==="
                sh """
                    if [ -z "${env.APP_ENDPOINT}" ] || [ "${env.APP_ENDPOINT}" = "YOUR_ELB_DNS_OR_IP" ]; then
                        echo "ELB endpoint not available or not set correctly"
                    else
                        # Test basic connectivity
                        echo "Testing basic connectivity to the application:"
                        curl -v --max-time 10 http://${env.APP_ENDPOINT}:5053 || echo "Application not reachable via ELB"
                        
                        # Test specific API endpoints if they exist
                        echo "Testing API endpoints:"
                        curl -v --max-time 10 http://${env.APP_ENDPOINT}:5053/api/tasks || echo "API endpoint not available"
                    fi
                """
            }
        }
    }

    post {
        always {
            echo "==== Pipeline execution completed ===="
        }
        success {
            echo "✅ Successfully installed eksctl, verified IAM role, created/used existing EKS cluster, deployed MySQL, deployed todo application with ELB, and checked deployment status"
        }
        failure {
            echo "❌ Pipeline failed, see logs for details"
        }
    }
}
