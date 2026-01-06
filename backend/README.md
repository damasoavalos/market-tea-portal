
# Market Tea Portal – Home Server Deployment (Debian 13)

This repository documents the complete deployment of the Market Tea internal web platform on a Debian 13 (trixie) home server.

The setup is designed to be:
- Reproducible
- LAN-only (no public exposure)
- Stable across Debian 13 environments
- Suitable for learning, testing, and internal production use
---
## Architecture Overview

![back-end-implementation.png](docs/images/back-end-implementation.png)
### Components
- Debian 13 – (Base OS)
- Python 3.13 - (Language runtime)
- Django – (Web Framework)
- Gunicorn – (WSGI server)
- Caddy – (Reverse proxy)
- Pi-hole – (DNS Resolution)
- PostgreSQL - (Database)
---
## Assumptions

| Item         | Value (example)     |
| ------------ | ------------------- |
| OS           | Debian GNU/Linux 13 |
| Hostname     | market-tea          |
| Server IP    | 192.168.1.92        |
| User         | damaso              |
| Project root | /srv/market-tea     |
Adjust IPs as needed, but keep consistency.

---
## Directory Layout

```
/srv/market-tea/
├── backend/        # Django project
├── venv/           # Python virtual environment
└── logs/           # Application logs
```
---
## 1. System Preparation

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```
---
## 2. Network (Static IP – Recommended)

Identify connection:
```bash
nmcli device status
```
Example static configuration:
```bash
sudo nmcli connection modify "FBI-HQ" \
  ipv4.method manual \
  ipv4.addresses 192.168.1.92/24 \
  ipv4.gateway 192.168.1.254 \
  ipv4.dns "192.168.1.254" \
  ipv6.method auto
```
Apply:
```bash
sudo nmcli connection down "FBI-HQ"
sudo nmcli connection up "FBI-HQ"
```
---
## 3. SSH Access

```bash
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
```
Test from another device:
```bash
ssh damaso@192.168.1.92
```
---
## 4. Firewall (UFW)

```bash
sudo apt install -y ufw

# 1. Allow SSH access first to prevent being locked out of the server
sudo ufw allow 22/tcp

# 2. DNS Resolution ports (Required for Pi-hole)
sudo ufw allow 53/tcp
sudo ufw allow 53/udp
sudo ufw allow 8081/tcp

# 3. Web Server ports (Required for Caddy / HTTP & HTTPS)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 4. Database port (PostgreSQL)
sudo ufw allow 5432/tcp

# 5. Additional ports (Gunicorn, Admin panels, or Development testing)
sudo ufw allow 8080/tcp

# 6. Enable the firewall and apply rules
sudo ufw enable
sudo ufw status
```
---
## 5. Django Backend

Clone or copy the project into backend/:
```bash
cd /srv/market-tea
git clone git@github.com:damasoavalos/market-tea-portal.git
```
## 6. Python Environment (Debian 13)

```bash
sudo apt install -y python3.13 python3.13-venv python3-pip build-essential
```

```bash
cd /srv/market-tea/market-tea-portal/backend
python3.13 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
```
Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```
---
## 7. Environment Variables

Create .env:
```bash
nano /srv/market-tea/backend/.env
```

Example:
```env
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=market-tea,tea-portal,ws400,192.168.1.92,localhost,127.0.0.1

DB_NAME=tea_inventory
DB_USER=markettea
DB_PASSWORD=********
DB_HOST=127.0.0.1
DB_PORT=5432
```
---
## 8. Django Settings (Critical)

In config/settings.py:
```python
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() in ("1","true","yes","on")

allowed_hosts = os.getenv("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in allowed_hosts.split(",") if h.strip()]
```
---
## 9. Test Django

```bash
python manage.py check
python manage.py runserver 127.0.0.1:8000
```
Test:
```bash
curl http://127.0.0.1:8000/reports/
```
 Stop the dev server.

---
## 10. Gunicorn (WSGI Server)

```bash
pip install gunicorn
```

Test run:
```bash
gunicorn market_tea_portal.wsgi:application \
  --bind 127.0.0.1:8000
```
---

## 11. systemd Service – Waitress

Create service file:
```bash
sudo nano /etc/systemd/system/market-tea-portal.service
```

```ini
[Unit]
Description=Market Tea Django Application
After=network.target postgresql.service

[Service]
User=youruser
Group=www-data
WorkingDirectory=/srv/market-tea/market-tea-portal
Environment="DJANGO_SETTINGS_MODULE=market_tea_portal.settings.production"
ExecStart=/srv/market-tea/market-tea-portal/venv/bin/gunicorn \
          market_tea_portal.wsgi:application \
          --bind 127.0.0.1:8000 \
          --workers 3

Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable market-tea
sudo systemctl start market-tea
sudo systemctl status market-tea

```
---
## 12. Caddy (Reverse Proxy)

Install:
```bash
sudo apt install -y caddy
```

Edit config:
```bash
sudo nano /etc/caddy/Caddyfile
```

```caddyfile
:80 {
	reverse_proxy localhost:8000
	log {
		output file /var/log/caddy/tea_portal.log
	}
}

http://pihole.tea-portal {
	reverse_proxy localhost:8081
	log {
		output file /var/log/caddy/pihole.log
	}
}
```

Restart:
```bash
sudo systemctl restart caddy
```
---
## 13. Pi-hole (DNS)

Install:
```bash
curl -fsSL https://install.pi-hole.net | sudo bash
```
Allow LAN queries:
```bash
sudo pihole-FTL --config dns.listeningMode ALL
sudo systemctl restart pihole-FTL
```
---
## 14. Router Configuration (TELUS)

In LAN → DHCP:
- DNS Server: 192.168.1.92
Save and reboot the router.
---
## 15. Pi-hole Local DNS Records

Pi-hole UI → Local DNS → DNS Records

| Hostname          | IP           |
| ----------------- | ------------ |
| tea-portal        | 192.168.1.92 |
| pihole.tea-portal | 192.168.1.92 |

---
## 16. Verification

```bash
nslookup tea-portal
```
Browser:
```
http://tea-portal/reports/
```
---
## 17. Service Status

```bash
systemctl status market-tea-portal.service
systemctl status caddy
systemctl status pihole-FTL
```
---

