# 🚀 Family Todo App
![image]([https://github.com/user-attachments/assets/132c6b79-0b1d-4142-8886-93c5bdb2e178](https://github.com/Ben-levi/AWS_APP/blob/main/Gemini_Generated_Image_uswm9duswm9duswm.png))
![image](https://github.com/user-attachments/assets/132c6b79-0b1d-4142-8886-93c5bdb2e178)

## Overview
A modern web application to manage family tasks, built with Flask and deployed on AWS EKS with a MySQL database and Grafana monitoring.

<div align="center">
    <h2 style="font-size: 2rem">
        <a href="http://a89728f2aaa2840b0989d6d870c0d333-6131c0b6a1c8950f.elb.us-east-1.amazonaws.com:5053/welcome">
            🔗 FAMILY TODO APP DEMO LINK 🔗
        </a>
    </h2>
</div>

<div align="center">
    <h3>
        <a href="https://github.com/Ben-levi/AWS_APP/raw/refs/heads/main/Demo_record.mp4">🎬 Watch Demo Video 🎬</a>
    </h3>
    <em>Coming soon! Check back for a full demonstration of app features.</em>
</div>

## 📋 Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Infrastructure](#infrastructure)
- [CI/CD Pipeline](#ci-cd-pipeline)
- [Monitoring](#monitoring)
- [Setup & Deployment](#setup--deployment)
- [Future Enhancements](#future-enhancements)

## ✨ Features

- **Task Management**: Create, update, delete, and mark tasks as complete
- **Family Assignments**: Assign tasks to specific family members
- **Priority Levels**: Set importance of tasks with visual indicators
- **Due Dates**: Schedule tasks with deadline notifications
- **Categories**: Organize tasks by type
- 
## 🏗️ Architecture

```
┌─────────────────┐      ┌─────────────────┐     ┌─────────────────┐
│   AWS Services  │──────▶  AWS ELB/ALB    │────▶│  Kubernetes    │
└─────────────────┘      └─────────────────┘     │  Cluster (EKS)  │
                                                 │                 │
┌─────────────────┐                              │  ┌───────────┐  │
│    Grafana      │◀─────────────────────────────┼──┤ Flask App │  │
│   Monitoring    │                              │  └───────────┘  │
└─────────────────┘                              │                 │
                                                 └────────┬────────┘
┌─────────────────┐                                       │
│    Jenkins      │                                       │
│    CI/CD        │                                       ▼
└─────────────────┘                              ┌─────────────────┐
                                                 │    MySQL RDS    │
                                                 └─────────────────┘
```

## 🛠️ Technology Stack

- **Frontend**: HTML5, JavaScript
- **Backend**: Python, Flask
- **Database**: MySQL
- **Containerization**: Docker
- **Orchestration**: Kubernetes (AWS EKS)
- **CI/CD**: Jenkins
- **Monitoring**: Grafana, Prometheus
- **Infrastructure**: AWS (EKS, ELB, S3)

## ☁️ Infrastructure

The application is fully deployed on AWS with:

- **EKS (Elastic Kubernetes Service)**: Managing containerized application
- **Elastic Load Balancer**: Handling traffic distribution
- **EC2**: Supporting infrastructure components
- **IAM**: Managing access control
- **VPC/Subnets**: Network isolation and security

## 🔄 CI/CD Pipeline

A robust Jenkins pipeline automates the deployment process:

1. **Code Commit**: Developer pushes to Git repository
2. **Build**: Jenkins triggers build job
3. **Test**: Automated tests are executed
4. **Container Build**: Docker image created and pushed to registry
5. **Deploy**: New version deployed to Kubernetes cluster
6. **Verification**: Health checks confirm successful deployment

## 📊 Monitoring

Comprehensive monitoring with Grafana dashboards for:

- **Application Health**: Response times, error rates, requests/second
- **Database Performance**: Query latency, connections, table stats
- **Infrastructure Metrics**: CPU, memory, network utilization
- **Custom Alerts**: Notifications for critical thresholds

## 🚀 Setup & Deployment

### Prerequisites
- AWS Account with necessary permissions
- kubectl and AWS CLI configured
- Docker installed

### Deployment Steps

1. **Clone the repository**
   ```
   git clone https://github.com/Ben-levi/AWS_APP.git
   cd family-todo-app
   ```

2. **Configure AWS resources**
   ```
   terraform init
   terraform apply
   ```

3. **Deploy to Kubernetes**
   ```
   kubectl apply -f kubernetes/
   ```

4. **Access the application**
   Visit: http://a89728f2aaa2840b0989d6d870c0d333-6131c0b6a1c8950f.elb.us-east-1.amazonaws.com:5053/welcome

## 🔮 Future Enhancements

- **Analytics Dashboard**: Track family task completion trends
- **Reward System**: Gamification elements for task completion
- **Multi-language Support**: Internationalization for global families

## 📜 License

## 👥 Contributors

- Your Name (@yourusername)

---

<div align="center">
    <p>Made with ❤️ for families everywhere</p>
</div>
