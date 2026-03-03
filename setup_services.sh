#!/bin/bash
sudo bash -c 'cat << EOF > /etc/systemd/system/aistore-backend.service
[Unit]
Description=AI Store Backend
After=network.target

[Service]
Type=simple
User=vscode
WorkingDirectory=/workspaces/AI_Store
ExecStart=/usr/local/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF'

sudo bash -c 'cat << EOF > /etc/systemd/system/cloudflared.service
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=simple
User=vscode
Environment="TUNNEL_TOKEN=eyJhIjoiMTM2ZWExODUwYzVjM2VlMWM3Yjk4MjllYWQ3Mzg1M2YiLCJ0IjoiZGRkMGQyMGEtNjNlMi00YThlLWExOTItZTdjNDFlMGVmNmIyIiwicyI6Ik1HUTVOalkxTkRjdE5tWTVaaTAwT1RZekxXRTVNRFV0TnpjNU1UZzRaREJoT1RFNCJ9"
ExecStart=/usr/local/bin/cloudflared tunnel run
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF'

sudo systemctl daemon-reload
sudo systemctl enable aistore-backend cloudflared
sudo systemctl restart aistore-backend cloudflared
sudo systemctl status aistore-backend cloudflared --no-pager
