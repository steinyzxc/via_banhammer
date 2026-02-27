# Step-by-step: Deploy to a new VM

Assumes a fresh Ubuntu/Debian VM (or similar) and that you use GitHub Actions to deploy.

---

## 1. Create and access the VM

- Create a VM (e.g. in a cloud provider). Note the public IP or hostname.
- SSH in as root or as a user with sudo:
  ```bash
  ssh root@YOUR_VM_IP
  ```
  (Replace with your user if not root.)

---

## 2. Install Python 3.10+ and create deploy user (optional)

If the image doesn’t have Python 3.10+:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
python3 --version   # must be 3.10+
```

To use a dedicated deploy user (recommended):

```bash
adduser deploy
usermod -aG sudo deploy
su - deploy
```

Use this user for the next steps and for GitHub secrets. If you stay as root, use `root` as `SSH_USER` later.

---

## 3. Allow SSH key login

On your **local machine** (not the VM), generate a key for deploy if you don’t have one:

```bash
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/github_deploy -N ""
```

On the **VM**, add the **public** key to the deploy user (or root):

```bash
mkdir -p ~/.ssh
echo "PASTE_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

Test from your machine:

```bash
ssh -i ~/.ssh/github_deploy deploy@YOUR_VM_IP
```

(Use `root@YOUR_VM_IP` if you deploy as root.)

---

## 4. One-time app directory and systemd on the VM

Still on the **VM**, as the user you will use for deploy (e.g. `deploy` or `root`):

```bash
# App directory (must match workflow DEPLOY_PATH)
sudo mkdir -p /opt/telegram-bot-filter
sudo chown $USER:$USER /opt/telegram-bot-filter
```

Copy the systemd unit from your repo (or create it manually):

```bash
# If you have the repo on the VM (e.g. cloned or copied):
sudo cp /path/to/deploy/telegram-bot-filter.service /etc/systemd/system/

# Or create the file directly:
sudo nano /etc/systemd/system/telegram-bot-filter.service
```

Paste this (path must be `/opt/telegram-bot-filter`):

```ini
[Unit]
Description=Via-bot filter Telegram bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/telegram-bot-filter
ExecStart=/opt/telegram-bot-filter/.venv/bin/python main.py
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot-filter
```

Allow the deploy user to restart the service without a password (replace `deploy` with your deploy user):

```bash
sudo visudo
```

Add this line at the end (one line):

```
deploy ALL=(ALL) NOPASSWD: /bin/systemctl restart telegram-bot-filter
```

Save and exit. If you deploy as **root**, you can skip this line.

---

## 5. GitHub repository secrets

In GitHub: repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**. Add:

| Name             | Value |
|------------------|--------|
| `BOT_TOKEN`      | Token from @BotFather |
| `SSH_HOST`       | VM IP or hostname (e.g. `12.34.56.78` or `vm.example.com`) |
| `SSH_USER`       | User you SSH as (e.g. `deploy` or `root`) |
| `SSH_PRIVATE_KEY`| Full contents of the **private** key (e.g. `~/.ssh/github_deploy`) |

To copy the private key on your machine:

```bash
cat ~/.ssh/github_deploy
```

Paste the whole output (including `-----BEGIN ... KEY-----` and `-----END ... KEY-----`) into the `SSH_PRIVATE_KEY` secret.

---

## 6. Run the deploy workflow

1. In GitHub: **Actions** → **Deploy** → **Run workflow** → **Run workflow**.
2. Wait for the job to finish (green check).
3. On the VM, start the service (first time only):

```bash
sudo systemctl start telegram-bot-filter
sudo systemctl status telegram-bot-filter
```

If the workflow already ran and the service was enabled, it may start automatically after the first successful deploy; if not, the step above starts it.

---

## 7. Logs on the server

The bot runs as the `telegram-bot-filter` systemd service. To view logs:

```bash
sudo journalctl -u telegram-bot-filter -f    # follow (live)
sudo journalctl -u telegram-bot-filter -n 100   # last 100 lines
sudo journalctl -u telegram-bot-filter --since today
```

---

## 8. Later deploys

After the first deploy, every time you run **Actions → Deploy → Run workflow**, the workflow will:

- Rsync the repo to `/opt/telegram-bot-filter`
- Write `.env` from `BOT_TOKEN`
- Install dependencies in the venv
- Restart `telegram-bot-filter` if the service is active

No need to SSH for routine updates.

---

## Troubleshooting

- **Permission denied (publickey)**  
  Check `SSH_PRIVATE_KEY` (full key, no extra spaces) and that the matching public key is in `~/.ssh/authorized_keys` on the VM.

- **Rsync error 13 (permission denied)**  
  The deploy user must have write access to `/opt/telegram-bot-filter`. Run `sudo chown -R $USER:$USER /opt/telegram-bot-filter` (as the user you use for `SSH_USER`).

- **Bot not responding**  
  On the VM: `sudo journalctl -u telegram-bot-filter -f`. Check for Python errors or missing `BOT_TOKEN`.

- **sudo systemctl restart asks for password**  
  Fix the `visudo` line for the deploy user, or deploy as root and use `SSH_USER=root`.

- **Python or venv errors**  
  Ensure Python 3.10+ is installed (`python3 --version`) and that the workflow step runs in `/opt/telegram-bot-filter` with the venv activated (the workflow creates it if missing).
