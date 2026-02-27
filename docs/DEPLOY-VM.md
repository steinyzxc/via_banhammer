# Step-by-step: Deploy to a new VM (Docker)

Deploy via GitHub Actions: code is copied to the server and run with `docker compose up -d --build`. No systemd.

---

## 1. Create and access the VM

- Create a VM (e.g. in a cloud provider). Note the public IP or hostname.
- SSH in:
  ```bash
  ssh root@YOUR_VM_IP
  ```
  (Or another user with sudo.)

---

## 2. Install Docker and Docker Compose

On Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Check:

```bash
docker --version
docker compose version
```

Optional: allow your deploy user to run Docker without sudo:

```bash
sudo usermod -aG docker $USER
# log out and back in
```

---

## 3. Deploy user and SSH key (optional)

To use a dedicated deploy user:

```bash
adduser deploy
usermod -aG sudo deploy
usermod -aG docker deploy
```

On your **local machine**, generate an SSH key for deploy:

```bash
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/github_deploy -N ""
```

On the **VM**, add the **public** key to the deploy user:

```bash
sudo -u deploy mkdir -p /home/deploy/.ssh
echo "PASTE_PUBLIC_KEY_HERE" | sudo tee -a /home/deploy/.ssh/authorized_keys
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

Test:

```bash
ssh -i ~/.ssh/github_deploy deploy@YOUR_VM_IP
```

Use `deploy` (or your user) as `SSH_USER` in GitHub secrets.

---

## 4. One-time: app directory on the VM

As the user you will use for deploy:

```bash
sudo mkdir -p /opt/telegram-bot-filter
sudo chown -R $USER:$USER /opt/telegram-bot-filter
```

No systemd unit. The workflow will put the code here and run Docker.

---

## 5. GitHub repository secrets

In GitHub: repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**. Add:

| Name             | Value |
|------------------|--------|
| `BOT_TOKEN`      | Token from @BotFather |
| `SSH_HOST`       | VM IP or hostname |
| `SSH_USER`       | User (e.g. `deploy` or `root`) |
| `SSH_PRIVATE_KEY`| Full contents of the **private** key |

---

## 6. Run the deploy workflow

1. In GitHub: **Actions** → **Deploy** → **Run workflow** → **Run workflow**.
2. Wait for the job to finish.

The workflow will:

- Copy the repo (as a tarball) to the server
- Extract into `/opt/telegram-bot-filter`
- Write `.env` with `BOT_TOKEN`
- Run `docker compose up -d --build`

The bot runs in a container. Data (SQLite DB) is stored in the Docker volume `bot_data`.

---

## 7. Logs

```bash
cd /opt/telegram-bot-filter
docker compose logs -f
```

---

## 8. Later deploys

Run **Actions → Deploy → Run workflow** again. Same steps: fresh code, `docker compose up -d --build`. Volume keeps the DB.

---

## Troubleshooting

- **Permission denied (publickey)**  
  Check `SSH_PRIVATE_KEY` and that the public key is in `~/.ssh/authorized_keys` on the VM.

- **Permission denied when creating /opt/telegram-bot-filter**  
  Run `sudo mkdir -p /opt/telegram-bot-filter && sudo chown $USER /opt/telegram-bot-filter` as the deploy user.

- **docker: command not found**  
  Install Docker and Docker Compose (step 2). If using a non-root user, add them to the `docker` group.

- **Bot not responding**  
  Check `docker compose logs` in the deploy path. Ensure `BOT_TOKEN` is set in GitHub secrets.
