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
                            APP_POD=$(kubectl get pods -n ${env.APP_NS} -l app=todo-app -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
                            if [ -n "$APP_POD" ]; then
                                echo "Testing network connectivity from $APP_POD to MySQL service:"
                                kubectl exec -it $APP_POD -n ${env.APP_NS} -- bash -c "nc -zvw3 mysql.${env.MYSQL_NS}.svc.cluster.local 3306" || echo "MySQL connectivity check failed"
                                
                                # Test DNS resolution
                                echo "Testing DNS resolution for MySQL service:"
                                kubectl exec -it $APP_POD -n ${env.APP_NS} -- bash -c "nslookup mysql.${env.MYSQL_NS}.svc.cluster.local" || echo "DNS resolution failed"
                                
                                # Check environment variables in app pod
                                echo "Checking environment variables in application pod:"
                                kubectl exec -it $APP_POD -n ${env.APP_NS} -- bash -c "env | grep -i -E \'mysql|db|database\'" || echo "No MySQL environment variables found"
                            fi
                            
                            echo "Describing todo-service (ELB):"
                            kubectl describe svc todo-service -n ${env.APP_NS}
                            
                            echo "Retrieving ELB endpoint:"
                            ELB_ENDPOINT=$(kubectl get svc todo-service -n ${env.APP_NS} -o jsonpath="{.status.loadBalancer.ingress[0].hostname}")
                            echo "ELB Endpoint: $ELB_ENDPOINT"
                            
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
                            MYSQL_POD=$(kubectl get pods -n ${env.MYSQL_NS} -l app=mysql -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
                            
                            if [ -n "$MYSQL_POD" ]; then
                                echo "Checking MySQL databases and tables:"
                                kubectl exec -it $MYSQL_POD -n ${env.MYSQL_NS} -- mysql -u root -ppassword -e "SHOW DATABASES;"
                                kubectl exec -it $MYSQL_POD -n ${env.MYSQL_NS} -- mysql -u root -ppassword -e "USE todos; SHOW TABLES;" || echo "Todo database not found or tables not created"
                                
                                # Check if the todos database exists, if not create it
                                echo "Ensuring todos database exists:"
                                kubectl exec -it $MYSQL_POD -n ${env.MYSQL_NS} -- mysql -u root -ppassword -e "CREATE DATABASE IF NOT EXISTS todos;"
                                
                                # Check if tasks table exists, if not create it
                                echo "Ensuring tasks table exists:"
                                kubectl exec -it $MYSQL_POD -n ${env.MYSQL_NS} -- mysql -u root -ppassword -e "USE todos; CREATE TABLE IF NOT EXISTS tasks (id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(255) NOT NULL, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
                                
                                # Insert test data
                                echo "Inserting test data:"
                                kubectl exec -it $MYSQL_POD -n ${env.MYSQL_NS} -- mysql -u root -ppassword -e "USE todos; INSERT INTO tasks (title, description) VALUES ('Test Task', 'This is a test task');"
                                
                                # Check data
                                echo "Checking inserted data:"
                                kubectl exec -it $MYSQL_POD -n ${env.MYSQL_NS} -- mysql -u root -ppassword -e "USE todos; SELECT * FROM tasks;"
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
