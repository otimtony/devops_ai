# Deploying DevOpsAI on a free AWS account

This guide runs the DevOpsAI web UI on a single Amazon EC2 instance, using Docker, within the AWS free tier. For local development setup, see [README.md](README.md).

```
your browser ──► EC2 instance (Ubuntu)
                   ├── nginx :80 (password login)
                   └── Docker container :7860 (DevOpsAI)
                         └── volume: SQLite incident database
```

The whole setup takes about 30 minutes.

## Before you start

### What you need

- An AWS account.
- An OpenAI API key. The agents use `gpt-4o-mini`, with `gpt-4o` as a fallback. OpenAI usage is billed by OpenAI and is not covered by the AWS free tier.
- An SSH client. macOS, Linux and Windows 10+ have one built in (`ssh`).
- The project in a Git repository the instance can clone, for example on GitHub.

### What the free tier covers

The AWS free tier depends on when your account was created:

- **Accounts created on or after 15 July 2025** are on the *Free plan*. You get AWS credits (up to $200) to use within 6 months, and you can only launch instance types marked **Free tier eligible**, such as `t3.micro` and `t3.small`.
- **Older accounts** get 750 hours a month of `t2.micro` or `t3.micro` for the first 12 months.

Either way, everything in this guide fits: one small instance running all month, a 20 GB disk, and a public IP address. The launch wizard labels instance types **Free tier eligible**; only pick one of those. AWS changes these terms from time to time, so check the [AWS Free Tier page](https://aws.amazon.com/free/) for your account.

### Access control

**The app has no login of its own.** Anyone who can reach it can submit incidents (spending your OpenAI credits), approve or reject reports, and read every approved report. This guide protects it in two ways:

1. The AWS firewall (security group) only lets in IP addresses you choose.
2. nginx asks for a username and password before showing the app.

## Step 1: Set a billing alert

Do this first, so a mistake can't run up a bill unnoticed.

1. In the AWS console, open **Billing and Cost Management → Budgets → Create budget**.
2. Choose the **Zero spend budget** template.
3. Enter your email address and click **Create budget**.

AWS will email you as soon as anything costs money.

## Step 2: Launch the EC2 instance

1. In the AWS console, pick a region close to you (top right), then open **EC2 → Instances → Launch instances**.
2. Fill in the form:

   | Setting | Value |
   |---|---|
   | Name | `devops-ai` |
   | AMI | **Ubuntu Server 24.04 LTS**, 64-bit (x86) |
   | Instance type | `t3.small` if it is marked Free tier eligible; otherwise `t3.micro` (or `t2.micro`) |
   | Key pair | **Create new key pair** → RSA, `.pem` → download it and keep it safe |
   | Storage | **20 GiB** gp3. The default 8 GiB is too small for the Docker image. |

3. Under **Network settings**, click **Edit** and set up the security group:

   | Type | Port | Source | Why |
   |---|---|---|---|
   | SSH | 22 | **My IP** | So you can log in to the server |
   | HTTP | 80 | **My IP**, plus any teammates' IP addresses | So you can open the app |

   Do not choose **Anywhere (0.0.0.0/0)** for either rule. Do not open port 7860.

4. Click **Launch instance**. When it shows **Running**, copy its **Public IPv4 address**. This guide calls it `<PUBLIC_IP>`.

The public IP changes if you stop and start the instance. If you want a fixed address, allocate an **Elastic IP** under **EC2 → Elastic IPs** and associate it with the instance. It's free while attached to a running instance, but costs money while the instance is stopped.

## Step 3: Connect to the instance

On macOS or Linux:

```bash
chmod 400 devops-ai.pem
ssh -i devops-ai.pem ubuntu@<PUBLIC_IP>
```

On Windows (PowerShell):

```powershell
ssh -i .\devops-ai.pem ubuntu@<PUBLIC_IP>
```

If Windows complains the key's permissions are too open, use **EC2 → Instances → Connect → EC2 Instance Connect** in the console instead. It opens a terminal in the browser.

All remaining commands run on the instance.

## Step 4: Prepare the server

Install Docker, nginx and Git:

```bash
sudo apt update
sudo apt install -y docker.io nginx apache2-utils git
sudo usermod -aG docker ubuntu
```

Log out and back in (`exit`, then `ssh` again) so you can run `docker` without `sudo`.

**On a `t3.micro` or `t2.micro` (1 GB of memory), add swap space.** Without it, the Docker build or an investigation can run out of memory and crash. You can skip this on a `t3.small`.

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Step 5: Add the Docker files to the project

Do this on your own computer, in the project root, then commit and push. You only need to do it once.

`Dockerfile`:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies first so they are cached between code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

ENV GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860 \
    DATABASE_PATH=/app/data/devops_ai.db

EXPOSE 7860
CMD ["uv", "run", "--no-sync", "ui"]
```

`.dockerignore`, which keeps your local virtual environment, database and secrets out of the image:

```
.venv/
.env
data/
.git/
.pytest_cache/
**/__pycache__/
```

## Step 6: Build and run the app

Back on the instance, clone the project:

```bash
git clone <your-repo-url> ~/devops_ai
cd ~/devops_ai
```

For a private GitHub repository, use a [personal access token](https://docs.github.com/en/authentication/keeping-your-account-secure/managing-your-personal-access-tokens) as the password when Git asks.

Create the settings file and make it readable only by you:

```bash
cat > .env <<'EOF'
OPENAI_API_KEY=sk-your-key-here
ENVIRONMENT=production
EOF
chmod 600 .env
nano .env   # replace sk-your-key-here with your real key, then Ctrl+O, Enter, Ctrl+X
```

Build the image. This takes 5–10 minutes on a micro instance:

```bash
docker build -t devops-ai .
```

Start the container:

```bash
docker volume create devops-ai-data

docker run -d \
  --name devops-ai \
  --restart unless-stopped \
  -p 127.0.0.1:7860:7860 \
  --env-file .env \
  -v devops-ai-data:/app/data \
  devops-ai
```

- `-p 127.0.0.1:7860:7860` makes the app reachable only from the instance itself, so nginx is the only way in.
- `--restart unless-stopped` starts the app again after a crash or a reboot.
- `-v devops-ai-data:/app/data` keeps the incident database when the container is replaced. Without it, the history is lost on every update.

Check that it started:

```bash
docker logs devops-ai
curl -I http://127.0.0.1:7860
```

`curl` should return `HTTP/1.1 200 OK`. The first start can take up to a minute.

## Step 7: Put nginx and a password in front

Create a login. Replace `alice` with a username; you'll be asked for a password. Run it again without `-c` to add more users.

```bash
sudo htpasswd -c /etc/nginx/devops-ai.htpasswd alice
```

Create the site config:

```bash
sudo tee /etc/nginx/sites-available/devops-ai > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;

    auth_basic           "DevOpsAI";
    auth_basic_user_file /etc/nginx/devops-ai.htpasswd;

    location / {
        proxy_pass http://127.0.0.1:7860;
        proxy_http_version 1.1;

        # Gradio streams progress updates, so keep connections open and unbuffered.
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;

        # An investigation can take a few minutes.
        proxy_read_timeout 600s;
    }
}
EOF
```

Swap the default site for this one and reload nginx:

```bash
sudo rm /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/devops-ai /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Now open `http://<PUBLIC_IP>` in your browser. After logging in, you should see the DevOpsAI UI.

### About HTTPS

This setup uses plain HTTP, so the password and incident data are not encrypted in transit. The security group limits who can connect, which lowers the risk, but here are two ways to do better:

- **Free HTTPS with a domain:** point a domain or subdomain at the instance's Elastic IP, open port 443 in the security group, then run `sudo apt install -y certbot python3-certbot-nginx` and `sudo certbot --nginx -d your.domain.com`.
- **Only you need access:** skip nginx and port 80, and use an SSH tunnel. Everything goes through the encrypted SSH connection:

  ```bash
  ssh -i devops-ai.pem -L 7860:127.0.0.1:7860 ubuntu@<PUBLIC_IP>
  ```

  Then open `http://127.0.0.1:7860` on your own computer while that SSH session is open.

## Updating the app

```bash
cd ~/devops_ai
git pull
docker build -t devops-ai .
docker rm -f devops-ai
# then run the same `docker run` command as in Step 6
```

The database is on the volume, so it carries over to the new container. Any database change is applied automatically when the app starts.

## Configuration reference

Put these in `~/devops_ai/.env` and recreate the container to apply changes.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | – | API key used by the agents |
| `ENVIRONMENT` | No | `development` | Label for the deployment, for example `production` |
| `MAX_INCIDENT_DESCRIPTION_CHARS` | No | `5000` | Longest incident description accepted |
| `MAX_LOG_SAMPLE_CHARS` | No | `20000` | Longest log sample accepted |

The Dockerfile already sets `GRADIO_SERVER_NAME`, `GRADIO_SERVER_PORT` and `DATABASE_PATH` for the container. Don't change them.

Never commit `.env` or build the API key into the image.

## Operating notes

- **Back up the database.** Copying the file while the app is running can give a broken copy, so use SQLite's backup command, then download it to your computer:

  ```bash
  # on the instance
  docker exec devops-ai uv run --no-sync python -c "import sqlite3; s=sqlite3.connect('/app/data/devops_ai.db'); d=sqlite3.connect('/app/data/backup.db'); s.backup(d)"
  docker cp devops-ai:/app/data/backup.db ~/devops_ai-$(date +%F).db

  # on your computer
  scp -i devops-ai.pem ubuntu@<PUBLIC_IP>:~/devops_ai-*.db .
  ```

- **Your IP address changed?** If you suddenly can't connect, update the **My IP** rules in the instance's security group (**EC2 → Security Groups → Edit inbound rules**).
- **Investigations run one at a time.** If two people click Investigate together, the second one waits until the first finishes.
- **Run one instance only.** The history is a single SQLite file on the instance's disk, so don't scale this out to several instances.
- **Secrets in logs.** Logs are masked for common secret patterns before they reach the model or the database. The masking only catches values of 8 or more characters, so ask users not to paste credentials anyway.
- **OpenAI costs.** Every investigation makes several OpenAI calls. Set a monthly usage limit on the API key in the OpenAI dashboard.

## Stopping or removing everything

- **Pause it:** **EC2 → Instances → Instance state → Stop**. A stopped instance isn't charged for compute, but its disk still counts towards your free storage, and an attached Elastic IP is charged while stopped.
- **Remove it for good:** back up the database first, then **Terminate** the instance, release any Elastic IP, and delete the security group and key pair.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Browser times out on `http://<PUBLIC_IP>` | Security group doesn't allow your IP, or the IP changed | Update the HTTP rule to **My IP** |
| `502 Bad Gateway` | The container isn't running yet or crashed | `docker ps -a` and `docker logs devops-ai` |
| `OPENAI_API_KEY is not set` in the logs | Key missing from `.env` | Fix `.env`, then `docker rm -f devops-ai` and `docker run` again |
| Build or investigation dies, `Killed` in output | Out of memory on a 1 GB instance | Add swap (Step 4) |
| `no space left on device` | Disk too small | Use 20 GiB, or free space with `docker system prune` |
| Agent progress freezes | nginx buffering or timeout | Check `proxy_buffering off` and `proxy_read_timeout` in the nginx config |
| History empty after an update | Container started without the volume | Always include `-v devops-ai-data:/app/data` |
