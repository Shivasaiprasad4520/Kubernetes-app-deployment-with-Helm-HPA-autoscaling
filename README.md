# Kubernetes-app-deployment-with-Helm-HPA-autoscaling
Kubernetes app deployment with Helm + HPA autoscaling

<img width="1440" height="760" alt="image" src="https://github.com/user-attachments/assets/d01db230-d3f0-4529-bccc-7c7fc76cc345" />

# Install prerequisites on your local machine (AWS CLI + eksctl + kubectl + Helm — all needed before touching EKS)

## Step:1.1 Install AWS CLI

        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        sudo ./aws/install
        aws --version   # confirm: aws-cli/2.x.x

## Configure AWS credentials

        aws configure
            AWS Access Key ID:     (your IAM user key)
            AWS Secret Access Key: (your IAM user secret)
            Default region:        ap-south-1
            Default output format: json

        aws sts get-caller-identity   # must return your account ID

## step:1.2 Install eksctl


        curl --silent --location \
          "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" \
          | tar xz -C /tmp
        sudo mv /tmp/eksctl /usr/local/bin
        eksctl version   # confirm install

## step:1.3 Install kubectl

        curl -LO "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
        sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
        kubectl version --client

## step:1.4 Install helm

        curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
        helm version

## step:2 Write a Docker for the Application

~> here we use *Gunicorn* a production-grade WSGI HTTP server for Python apps like Flask.

        CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]

## step:2.1 Update requirements.txt inside app/ folder

## step:3.1 Build and push image to AWS ECR

        # Login to ECR
        aws ecr get-login-password --region ap-south-1 | \
          docker login --username AWS --password-stdin \
          YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com

       # Build image
       docker build -t college-portal:1.0 .

       # Tag for ECR
       docker tag college-portal:1.0 \
         YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/college-portal:1.0

       # Create ECR repo if not exists
       aws ecr create-repository --repository-name college-portal --region ap-south-

       # Push
       docker push YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/college-portal:1.0

## step:4.1 Create EKS cluster with eksctl

        eksctl create cluster -f cluster.yaml

        # Watch progress:
        eksctl get cluster --region ap-south-1

        # Once done — configure kubectl automatically:
        aws eks update-kubeconfig \
          --region ap-south-1 \
          --name college-portal-cluster

        # Verify nodes are ready:
        kubectl get nodes
        # Should show 2 nodes with STATUS: Ready

## step:5.1 Enable Metrics Server on EKS

        ## to downloads Metrics Server YAML Locally
        curl -LO https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

        ## Edit YAML Before Installing
        nano components.yaml

        Find this section:
        args:
        
        Add THIS line:
        - --kubelet-insecure-tls

        Save File
        CTRL + O
        ENTER
        CTRL + X

        ## Reinstall Cleanly
        kubectl apply -f components.yaml

        # Wait 60 seconds then verify:
        kubectl get deployment metrics-server -n kube-system
        kubectl top nodes   # must return CPU/memory values not errors

## step:6.1 Create the Helm chart for college portal

        mkdir helm-college-portal && cd helm-college-portal
        helm create college-portal
        rm helm-college-portal/templates/*.yaml
        rm helm-college-portal/templates/NOTES.txt 2>/dev/null || true

        write "helm-college-portal/Chart.yaml"
        write "helm-college-portal/values.yaml"
        write "helm-college-portal/templates/configmap.yaml"
        write "helm-college-portal/templates/secret.yaml"
        write "helm-college-portal/templates/deployment.yaml"
        write "helm-college-portal/templates/service.yaml"
        write "helm-college-portal/templates/hpa.yaml"

## step:7.1 Deploy with Helm to EKS

        helm lint helm-college-portal/
        
    deploy
    
        helm install college-release helm-college-portal/

        # Watch all resources come up
        kubectl get all -w

        # Should show:
        # pod/college-release-deployment-xxx   Running
        # service/college-release-service      LoadBalancer   (pending → gets external IP)
        # deployment/college-release-deployment  1/1
        # horizontalpodautoscaler/college-release-hpa
        
## step:7.2 Get the public URL — this is your live app

        kubectl get svc college-release-service
        # EXTERNAL-IP column shows something like:
        # a1b2c3.ap-south-1.elb.amazonaws.com

        # Wait 2-3 min for ELB to provision, then open in browser:
        # http://a1b2c3.ap-south-1.elb.amazonaws.com

## step:7.3 Verify HPA is reading CPU correctly

        kubectl get hpa
        # TARGETS must show: 0%/50%  (not "unknown")
        # If shows unknown — metrics-server not ready, wait 2 min and retry
        
## step:8.1 Load test with Apache Bench to trigger HPA

##### Open TWO terminals — run both simultaneously

        # Terminal 1 — watch pods scale in real time (refresh every 3s)
        watch -n 3 "kubectl get hpa && echo '---' && kubectl get pods"

        # Terminal 2 — hammer the app with load
        sudo apt install apache2-utils -y
        ab -n 5000 -c 50 http://YOUR_ELB_URL/

        # Within 2-3 minutes you will see:
        # REPLICAS: 1 → 2 → 3 → 4 → 5 in Terminal 1
        
## step:9.1 Helm upgrade — push a change without downtime

        # Change image tag in values.yaml to 2.0, then:
        docker build -t college-portal:2.0 .
        docker tag college-portal:2.0 YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/college-portal:2.0
        docker push YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/college-portal:2.0

        helm upgrade college-release helm-college-portal/ \
          --set image.tag=2.0

        # Watch rolling update (zero downtime):
        kubectl rollout status deployment/college-release-deployment

        
        # View release history:
        helm history college-release

        # Rollback if needed:
        helm rollback college-release 1

## step:10 DELETE cluster after you're done 

        # Delete everything in this order:
        helm uninstall college-release          # removes K8s resources
        eksctl delete cluster -f cluster.yaml   # deletes EKS + EC2 nodes + ELB (~10 min)

        # Verify cluster is gone:
        eksctl get cluster --region ap-south-1
        # Should return: No clusters found

        # Also check AWS Console → EC2 → no running instances
        # AWS Console → EKS → no clusters
