# Flask CI/CD Pipeline with GitHub Actions, Amazon ECR and EC2

## 1. Project Overview

This project implements an end-to-end CI/CD pipeline for a Python Flask application using GitHub Actions.

The pipeline automatically:

1. Checks out the source code.
2. Installs Python dependencies.
3. Runs the pytest test suite.
4. Stops the pipeline if tests fail.
5. Builds a Docker image.
6. Tags the Docker image using the Git commit SHA.
7. Pushes the image to Amazon ECR.
8. Deploys the image to an Amazon EC2 instance using AWS Systems Manager (SSM).
9. Stops and removes the previously running container.
10. Starts the new container.
11. Verifies the deployment using the `/health` endpoint.
12. Sends a customized success or failure email notification.

---

## 2. Architecture

```text
Developer
    |
    | Push to main
    v
+----------------------+
| GitHub Repository    |
+----------+-----------+
           |
           v
+----------------------+
| GitHub Actions       |
| GitHub-hosted Runner |
+----------+-----------+
           |
           v
+----------------------+
| Python Tests         |
| pytest               |
+----------+-----------+
           |
         PASS
           |
           v
+----------------------+
| Docker Build         |
| Tag = Git SHA        |
+----------+-----------+
           |
           v
+----------------------+
| Amazon ECR           |
| Docker Image         |
+----------+-----------+
           |
           v
+----------------------+
| AWS Systems Manager  |
| Run Command / SSM    |
+----------+-----------+
           |
           v
+----------------------+
| Amazon EC2           |
|                      |
| docker pull         |
| docker stop         |
| docker rm            |
| docker run           |
| /health verification |
+----------+-----------+
           |
           v
+----------------------+
| Email Notification   |
| SUCCESS / FAILURE    |
+----------------------+
```

---

## 3. Technology Stack

| Component          | Technology                  |
| ------------------ | --------------------------- |
| Source Control     | GitHub                      |
| CI/CD              | GitHub Actions              |
| Runner             | GitHub-hosted Ubuntu runner |
| Application        | Python Flask                |
| Testing            | pytest                      |
| Containerization   | Docker                      |
| Container Registry | Amazon ECR                  |
| Compute            | Amazon EC2                  |
| Remote Deployment  | AWS Systems Manager         |
| Authentication     | GitHub OIDC + AWS IAM       |
| Notifications      | SMTP email                  |

---

## 4. Application

The application is a simple Python Flask application.

### Endpoints

| Endpoint      | Purpose                 | Expected Response |
| ------------- | ----------------------- | ----------------- |
| `/`           | Application home/status | HTTP 200          |
| `/health`     | Deployment health check | HTTP 200          |
| `/api/status` | Application status      | HTTP 200          |
| Invalid route | Negative test           | HTTP 404          |

The `/health` endpoint is used as the deployment verification gate.

A deployment is considered successful only when the new container starts successfully and the `/health` endpoint returns HTTP 200.

---

## 5. Repository Structure

```text
flask-cicd-assignment/
|
├── app.py
├── requirements.txt
├── Dockerfile
├── .gitignore
├── README.md
|
├── tests/
│   ├── __init__.py
│   └── test_app.py
|
└── .github/
    └── workflows/
        └── ci.yml
```

---

## 6. AWS Prerequisites

The following AWS resources are required before running the pipeline.

### Amazon ECR

A private ECR repository:

```text
flask-cicd-assignment
```

The Docker image is stored using the Git commit SHA as the image tag.

Example:

```text
<account-id>.dkr.ecr.<region>.amazonaws.com/flask-cicd-assignment:<commit-sha>
```

### Amazon EC2

An Amazon Linux 2023 EC2 instance is used as the deployment target.

The instance requires:

* Docker installed and running.
* AWS Systems Manager Agent installed and running.
* IAM instance role.
* Network connectivity to required AWS services.
* Application port configured as required.

---

## 7. EC2 IAM Role

The EC2 instance uses an IAM role with the following AWS managed policies:

```text
AmazonSSMManagedInstanceCore
AmazonEC2ContainerRegistryPullOnly
```

### AmazonSSMManagedInstanceCore

Allows the EC2 instance to communicate with AWS Systems Manager and receive Run Command operations.

### AmazonEC2ContainerRegistryPullOnly

Allows the EC2 instance to authenticate with Amazon ECR and pull container images.

---

## 8. GitHub Actions AWS Authentication

The GitHub Actions runner does not use long-lived AWS access keys.

GitHub Actions authenticates to AWS using OpenID Connect (OIDC).

The flow is:

```text
GitHub Actions
      |
      | OIDC token
      v
GitHub OIDC Provider
      |
      v
AWS IAM Role
      |
      v
Temporary AWS Credentials
```

The IAM role trust policy restricts access to the specific GitHub repository and main branch.

This avoids storing AWS access keys in GitHub.

---

## 9. GitHub Repository Variables

The following GitHub Actions variables are configured:

```text
AWS_REGION
ECR_REPOSITORY
EC2_INSTANCE_ID
```

Example:

```text
AWS_REGION=ap-south-1
ECR_REPOSITORY=flask-cicd-assignment
EC2_INSTANCE_ID=i-xxxxxxxxxxxxxxxxx
```

Actual values should be configured in GitHub and should not be hardcoded into the workflow.

---

## 10. GitHub Repository Secrets

The following secrets are configured:

```text
AWS_ROLE_ARN

MAIL_SERVER
MAIL_PORT
MAIL_USERNAME
MAIL_PASSWORD
MAIL_FROM
MAIL_TO
```

Sensitive credentials are stored in GitHub Secrets and are never committed to the repository.

---

## 11. CI/CD Pipeline

The workflow is triggered automatically whenever code is pushed to the `main` branch.

```text
Push to main
     |
     v
Checkout
     |
     v
Install dependencies
     |
     v
Run pytest
     |
     +---- FAIL ----> Stop pipeline
     |
    PASS
     |
     v
Docker build
     |
     v
Tag image with Git SHA
     |
     v
Push image to ECR
     |
     v
Deploy to EC2 using SSM
     |
     v
Pull image
     |
     v
Stop old container
     |
     v
Remove old container
     |
     v
Run new container
     |
     v
Health check
     |
   +---+---+
   |       |
 PASS     FAIL
   |       |
   v       v
Success  Failure
 Email    Email
```

---

## 12. Test Stage

The pipeline installs the Python dependencies:

```bash
pip install -r requirements.txt
```

and executes:

```bash
pytest -v
```

The build and deployment stages depend on the successful completion of the test stage.

Therefore:

```text
pytest PASS
    |
    +--> Build
            |
            +--> Push
                    |
                    +--> Deploy
```

If pytest fails, Docker build, ECR push and deployment do not execute.

---

## 13. Docker Image Tagging

Every Docker image is tagged using the Git commit SHA.

Example:

```text
flask-cicd-assignment:a81f3c9b7e2d4c...
```

This provides traceability between:

```text
Git commit
     |
     v
Docker image
     |
     v
ECR
     |
     v
EC2 deployment
```

The `latest` tag is not used as the deployment identifier.

---

## 14. Deployment to EC2

AWS Systems Manager Run Command is used instead of SSH.

The deployment command performs:

```text
1. Authenticate with ECR
2. Pull the SHA-tagged image
3. Stop existing flask-cicd-app container
4. Remove existing flask-cicd-app container
5. Start the new container
6. Wait for application startup
7. Execute /health check
```

The EC2 instance does not need an SSH connection from the GitHub Actions runner.

### Why SSM was selected

SSM was selected because:

* It avoids storing an SSH private key in GitHub.
* It avoids requiring SSH access from GitHub-hosted runners.
* The EC2 instance can be managed through AWS Systems Manager.
* Deployment commands can be executed remotely.
* The deployment process remains within the AWS control plane.

---

## 15. Deployment Verification

The deployment runs:

```bash
curl --fail http://localhost:5000/health
```

A successful HTTP 200 response is required.

If the container starts but the health check fails, the deployment job fails.

Therefore:

```text
Container starts
      |
      v
Health check
      |
  +---+---+
  |       |
 200     Error
  |       |
  v       v
PASS    FAILURE
```

---

## 16. Email Notifications

The pipeline sends customized email notifications.

### Successful deployment

The success email includes:

* Success indicator.
* Repository.
* Branch.
* Git commit SHA.
* Docker image tag.
* EC2 instance.
* Deployment status.
* Health check status.
* GitHub Actions run link.

### Failed pipeline

The failure email includes:

* Failure indicator.
* Repository.
* Branch.
* Git commit SHA.
* Failed stage.
* Individual job results.
* GitHub Actions run/log link.

The notification job executes even when an earlier pipeline stage fails.

---

## 17. Failure Handling

The pipeline is designed to stop at the appropriate stage.

### Test failure

```text
Test       FAILED
Build      SKIPPED
Push       SKIPPED
Deploy     SKIPPED
Notify     FAILURE EMAIL
```

### Build or ECR failure

```text
Test       SUCCESS
Build      FAILED
Deploy     SKIPPED
Notify     FAILURE EMAIL
```

### Deployment failure

```text
Test       SUCCESS
Build      SUCCESS
Push       SUCCESS
Deploy     FAILED
Notify     FAILURE EMAIL
```

### Complete success

```text
Test       SUCCESS
Build      SUCCESS
Push       SUCCESS
Deploy     SUCCESS
Health     SUCCESS
Notify     SUCCESS EMAIL
```

---

## 18. Manual Deployment

If GitHub Actions is temporarily unavailable, deployment can be reproduced manually from the EC2 instance.

### Authenticate with ECR

```bash
aws ecr get-login-password \
  --region <region> \
| docker login \
  --username AWS \
  --password-stdin \
  <account-id>.dkr.ecr.<region>.amazonaws.com
```

### Pull the image

```bash
docker pull \
  <account-id>.dkr.ecr.<region>.amazonaws.com/flask-cicd-assignment:<commit-sha>
```

### Stop existing container

```bash
docker stop flask-cicd-app || true
```

### Remove existing container

```bash
docker rm flask-cicd-app || true
```

### Run the new container

```bash
docker run -d \
  --name flask-cicd-app \
  -p 5000:5000 \
  <account-id>.dkr.ecr.<region>.amazonaws.com/flask-cicd-assignment:<commit-sha>
```

### Verify deployment

```bash
curl --fail http://localhost:5000/health
```

Expected response:

```json
{
  "status": "healthy"
}
```

---

## 19. Security Considerations

The implementation uses the following security practices:

* AWS credentials are not committed to GitHub.
* GitHub Actions uses OIDC for AWS authentication.
* AWS permissions are separated between GitHub Actions and EC2.
* EC2 uses an IAM role instead of hardcoded AWS credentials.
* ECR repository access is controlled through IAM.
* Email credentials are stored in GitHub Secrets.
* The deployment does not require SSH access from the GitHub-hosted runner.
* Docker images are identified using immutable Git commit SHA tags.

---

## 20. Troubleshooting

### GitHub Actions cannot authenticate to AWS

Check:

* GitHub OIDC provider exists in AWS.
* OIDC audience is `sts.amazonaws.com`.
* `AWS_ROLE_ARN` points to the correct IAM role.
* IAM trust policy matches the repository and branch.
* Workflow has:

```yaml
permissions:
  id-token: write
  contents: read
```

### EC2 does not appear in Systems Manager

Check:

```bash
sudo systemctl status amazon-ssm-agent
```

and:

```bash
sudo systemctl restart amazon-ssm-agent
```

Also verify that the EC2 IAM role contains:

```text
AmazonSSMManagedInstanceCore
```

### ECR pull fails on EC2

Check that the EC2 IAM role has:

```text
AmazonEC2ContainerRegistryPullOnly
```

and that the instance can reach Amazon ECR.

### Health check fails

Check:

```bash
docker ps
docker logs flask-cicd-app
curl http://localhost:5000/health
```

---

## 21. Conclusion

This project demonstrates an end-to-end CI/CD implementation using GitHub Actions and AWS.

The pipeline provides:

* Automated testing.
* Test-gated builds.
* Docker containerization.
* Git SHA-based image traceability.
* Amazon ECR image storage.
* Automated EC2 deployment.
* AWS Systems Manager-based remote execution.
* Deployment health verification.
* Customized success and failure notifications.

Repository:

`https://github.com/Ashwin1983/flask-cicd-assignment.git`
