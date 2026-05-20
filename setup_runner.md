# Runner VM Setup

## Requirements
- Ubuntu 24.04 Server
- 1 CPU, 1GB RAM, 10GB Disk

## Installation

### 1. Install dependencies
```bash
sudo apt-get update
sudo apt-get install -y curl wget git docker.io openssh-client
sudo systemctl enable docker
sudo systemctl start docker
```

### 2. Generate SSH key for deployment
```bash
ssh-keygen -t ed25519 -C "github-runner" -f ~/.ssh/deploy_key -N ""
cat ~/.ssh/deploy_key.pub
# Add this public key to target VM: ~/.ssh/authorized_keys
```

### 3. Install GitHub Actions Runner
Download and install from:
https://github.com/Ann0123-cyber/mywebapp/settings/actions/runners/new

```bash
mkdir actions-runner && cd actions-runner
# Follow instructions from GitHub
./config.sh --url https://github.com/Ann0123-cyber/mywebapp --token YOUR_TOKEN
sudo ./svc.sh install
sudo ./svc.sh start
```

### 4. Add GitHub Secrets
- `DEPLOY_HOST` — IP of target VM
- `DEPLOY_USER` — SSH user on target VM
- `DEPLOY_KEY` — private key (~/.ssh/deploy_key)

### Security Note
Stop or delete the runner VM after use to prevent unauthorized access.