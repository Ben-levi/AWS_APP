pipeline {
    agent any

    environment {
        EC2_HOST    = '54.144.194.189'
        SSH_USER    = 'ubuntu'
        SSH_CRED_ID = 'e3057e9e-d907-42db-881f-b8f699c8f692'
        AWS_REGION  = 'us-east-1'
        APP_ENDPOINT = 'YOUR_ELB_DNS_OR_IP'
        MYSQL_NS    = 'database'
        APP_NS      = 'application'
    }

    options {
        timeout(time: 5, unit: 'MINUTES')
    }

    stages {
        // [Previous stages remain the same]
        
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
                            cd AWS_APP/k8s
                            
                            # Apply ConfigMap and Secret
                            echo "Applying ConfigMap and Secret..."
                            kubectl apply -f configmap-and-secret.yaml -n ${env.APP_NS}
                            
                            # Apply the ConfigMaps for the improved application
                            echo "Applying improved app ConfigMaps..."
                            kubectl apply -f app-configmaps.yaml -n ${env.APP_NS}
                            
                            # Apply the deployment
                            echo "Applying deployment..."
                            kubectl apply -f deployment.yaml -n ${env.APP_NS}
                            
                            # Apply the ELB service
                            echo "Applying ELB service..."
                            kubectl apply -f service-elb.yaml -n ${env.APP_NS}
                            
                            # Wait for the application to be ready
                            echo "Waiting for application to be ready..."
                            DEPLOYMENT_NAME=\$(kubectl get deployments -n ${env.APP_NS} | grep todo | awk "{print \\\$1}")
                            kubectl wait --for=condition=available deployment/\$DEPLOYMENT_NAME -n ${env.APP_NS} --timeout=300s || echo "Timeout waiting for application deployment"
                        '
                    """
                }
            }
        }
        
        // [Remaining stages stay the same]
    }
}
