# Gate Camera Setup Guide (Production)

## Overview

The MTT gate camera system uses a Hikvision DS-2CD4A26FWD-IZS/P ANPR camera for:
- **Live video streaming** (RTSP via MediaMTX → WebRTC to browser)
- **PTZ zoom control** (ISAPI HTTP commands from backend)
- **ANPR plate detection** (camera alert stream or webhook → backend processing)

## Architecture

```
                    Internet
                       │
         ┌─────────────┴──────────────┐
         │   Router / Static IP       │
         │   178.218.200.228          │
         │                            │
         │   Port 554  → Camera:554   │  ← RTSP video
         │   Port 8080 → Camera:80    │  ← HTTP/ISAPI (PTZ + ANPR)
         └─────────────┬──────────────┘
                       │ LAN
         ┌─────────────┴──────────────┐
         │   Hikvision Camera         │
         │   192.168.0.240 (LAN)      │
         │                            │
         │   Port 80   → HTTP/ISAPI   │
         │   Port 554  → RTSP         │
         │   Port 8000 → SDK (unused) │
         └────────────────────────────┘


         ┌────────────────────────────┐
         │   Production Server        │
         │   mtt-pro-api.xlog.uz      │
         │                            │
         │   MediaMTX                 │
         │   ├─ :8554 RTSP re-stream  │
         │   ├─ :8889 WebRTC (WHEP)   │
         │   └─ :8888 HLS fallback    │
         │                            │
         │   Django Backend           │
         │   ├─ PTZ → Camera:8080     │
         │   ├─ ANPR stream listener  │
         │   └─ Webhook endpoint      │
         └────────────────────────────┘
```

## Step 1: Camera Network Configuration

### On the Hikvision Camera Web UI

Access the camera locally at `http://192.168.0.240` and configure:

**Network → Port Settings:**

| Setting | Value | Notes |
|---------|-------|-------|
| HTTP Port | `8080` | Changed from 80 to avoid router conflict |
| RTSP Port | `554` | Default, keep as-is |
| HTTPS Port | `443` | Default, keep as-is |
| Server Port | `8000` | SDK port, not used by MTT |

### On the Router

Set up TCP port forwarding rules:

| External Port | Internal IP:Port | Protocol | Purpose |
|---------------|------------------|----------|---------|
| `554` | `192.168.0.240:554` | TCP | RTSP video streaming |
| `8080` | `192.168.0.240:8080` | TCP | HTTP/ISAPI (PTZ + ANPR) |

> **Note:** Only TCP is needed. UDP is not required because RTSP uses TCP transport.

## Step 2: Backend Environment Variables

Add these to the production `.env` file on the server:

```env
# Gate Camera (Hikvision ANPR)
GATE_CAMERA_IP=178.218.200.228
GATE_CAMERA_PORT=8080
GATE_CAMERA_USER=admin
GATE_CAMERA_PASS=<camera-password>
```

After updating `.env`, restart the backend:

```bash
sudo systemctl restart mtt-terminal
```

## Step 3: MediaMTX Configuration

### Install MediaMTX

```bash
# Download latest release
wget https://github.com/bluenviron/mediamtx/releases/latest/download/mediamtx_v1.16.1_linux_amd64.tar.gz
tar xzf mediamtx_v1.16.1_linux_amd64.tar.gz
sudo mv mediamtx /usr/local/bin/
```

### Create Configuration File

Create `/etc/mediamtx/mediamtx.yml`:

```yaml
logLevel: info
logDestinations: [stdout]

readTimeout: 10s
writeTimeout: 10s
writeQueueSize: 512

authMethod: internal
authInternalUsers:
  - user: any
    ips: []
    permissions:
      - action: publish
      - action: read
      - action: playback
      - action: api

api: yes
apiAddress: 127.0.0.1:9997

metrics: no

# Protocol servers
rtsp: yes
rtspAddress: :8554

rtmp: no

hls: yes
hlsAddress: :8888
hlsSegmentDuration: 1s
hlsPartDuration: 200ms
hlsSegmentCount: 7

webrtc: yes
webrtcAddress: :8889
webrtcICEServers2:
  - url: stun:stun.l.google.com:19302
webrtcLocalTCPAddress: :8189

srt: no

# Camera streams
paths:
  # Main stream (1080p) — for recording/snapshots
  gate-main:
    source: rtsp://admin:<password-url-encoded>@178.218.200.228:554/Streaming/Channels/101
    sourceOnDemand: yes
    sourceOnDemandStartTimeout: 10s
    sourceOnDemandCloseAfter: 30s

  # Sub stream (lower res) — for live preview in browser
  gate-sub:
    source: rtsp://admin:<password-url-encoded>@178.218.200.228:554/Streaming/Channels/102
    sourceOnDemand: yes
    sourceOnDemandStartTimeout: 10s
    sourceOnDemandCloseAfter: 30s
```

> **Important:** If the camera password contains `@`, URL-encode it as `%40`.
> Example: `qwerty@12` → `qwerty%4012` in the RTSP URL.

### Create Systemd Service

Create `/etc/systemd/system/mtt-mediamtx.service`:

```ini
[Unit]
Description=MediaMTX RTSP/WebRTC Server for MTT Gate Camera
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/mediamtx /etc/mediamtx/mediamtx.yml
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mtt-mediamtx
sudo systemctl start mtt-mediamtx
sudo systemctl status mtt-mediamtx
```

### Nginx Proxy for WebRTC (Optional)

If the frontend needs to access WebRTC through the main domain, add to nginx config:

```nginx
# WebRTC WHEP endpoint
location /camera/ {
    proxy_pass http://127.0.0.1:8889/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

Then set in frontend `.env.production`:

```env
VITE_GATE_CAMERA_WEBRTC_URL=https://mtt-pro.xlog.uz/camera/gate-sub/whep
```

## Step 4: ANPR Detection Setup

There are two ways to receive plate detections:

### Option A: Alert Stream Listener (Recommended)

The backend pulls events from the camera's ISAPI alert stream. Run as a systemd service:

Create `/etc/systemd/system/mtt-anpr-listener.service`:

```ini
[Unit]
Description=MTT ANPR Listener (Hikvision Camera)
After=network.target mtt-terminal.service

[Service]
Type=simple
WorkingDirectory=/var/www/terminal-pro/backend
ExecStart=/var/www/terminal-pro/backend/.venv/bin/python manage.py listen_anpr
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable mtt-anpr-listener
sudo systemctl start mtt-anpr-listener

# Check logs
journalctl -u mtt-anpr-listener -f
```

### Option B: Webhook (Camera Pushes Events)

Configure the camera to POST detections to the backend.

**In Hikvision web UI → Configuration → Event → Smart Event → ANPR:**
1. Enable ANPR
2. Set HTTP notification URL: `https://mtt-pro-api.xlog.uz/api/gate/anpr-event/`
3. Set method: `POST`

The webhook endpoint uses IP-based access control (no JWT). The camera's public IP (`178.218.200.228`) is automatically whitelisted via `GATE_CAMERA_IP` in `.env`.

## Step 5: Verification

### Test Port Connectivity

```bash
# From the production server
nc -z -w 5 178.218.200.228 554 && echo "RTSP OK" || echo "RTSP FAIL"
nc -z -w 5 178.218.200.228 8080 && echo "ISAPI OK" || echo "ISAPI FAIL"
```

### Test ISAPI (Camera Info)

```bash
curl -s --digest -u "admin:<password>" \
  "http://178.218.200.228:8080/ISAPI/System/deviceInfo"
```

Expected: XML with `<model>DS-2CD4A26FWD-IZS/P</model>`

### Test RTSP Stream

```bash
ffprobe -v error -rtsp_transport tcp \
  -i "rtsp://admin:<password-encoded>@178.218.200.228:554/Streaming/Channels/102" \
  -show_entries stream=codec_name,width,height -print_format json
```

Expected: `H264, 704x576`

### Test MediaMTX

```bash
# Check paths status
curl -s http://127.0.0.1:9997/v3/paths/list | python3 -m json.tool

# Check WebRTC endpoint
curl -s -o /dev/null -w "%{http_code}" http://localhost:8889/gate-sub/whep
```

### Test PTZ Control

```bash
curl -X POST https://mtt-pro-api.xlog.uz/api/gate/camera/ptz/ \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{"action": "zoom_in", "speed": 50}'
```

## Troubleshooting

| Issue | Check |
|-------|-------|
| RTSP stream not connecting | Port 554 forwarded? `nc -z 178.218.200.228 554` |
| ISAPI returns 404 | Port 8080 forwarded? Camera HTTP port set to 8080? |
| ISAPI returns 401 | Wrong credentials — **do NOT retry more than 3 times** (camera locks out for 30 min) |
| MediaMTX shows "no readers" | Normal — `sourceOnDemand` only connects when someone watches |
| WebRTC black screen | Check MediaMTX logs: `journalctl -u mtt-mediamtx -f` |
| ANPR listener disconnects | Check `journalctl -u mtt-anpr-listener -f` — auto-reconnects with backoff |
| Webhook returns 403 | Camera IP doesn't match `GATE_CAMERA_IP` in `.env` |
| PTZ not responding | ISAPI port accessible? Test with curl first |

## Service Management Summary

```bash
# All camera-related services
sudo systemctl status mtt-mediamtx        # Video streaming
sudo systemctl status mtt-anpr-listener   # Plate detection

# Restart after config changes
sudo systemctl restart mtt-mediamtx
sudo systemctl restart mtt-anpr-listener

# View logs
journalctl -u mtt-mediamtx -f
journalctl -u mtt-anpr-listener -f
```

## Security Notes

- **Camera credentials** are stored in `.env` (gitignored) and `mediamtx.yml` (gitignored)
- **RTSP URLs** contain credentials — never commit `mediamtx.yml` to git
- **Webhook endpoint** uses `AllowAny` permission with IP whitelist — only the camera IP and localhost are accepted
- **Camera lockout**: Hikvision locks after ~5 failed auth attempts for 30 minutes — never try multiple passwords
- **Port 8080 exposure**: Only expose if PTZ/ANPR is needed remotely. On local network, use `192.168.0.240:80` directly
