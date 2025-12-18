# Relocating Print Server to New Network

Quick guide for moving the print server to a new location/network.

---

## What You Need

- The print server (Dell Mini)
- Power cable
- USB cable for Brother printer
- WiFi password for new network (or Ethernet cable)
- A computer/phone to SSH from

---

## Step 1: Connect Server to New Network

### Option A: WiFi

1. Connect a monitor and keyboard temporarily, or SSH if you have any connectivity

2. Run:
   ```bash
   sudo nmtui
   ```

3. Select **"Activate a connection"**

4. Find your WiFi network, select it

5. Enter the password

6. Back out and quit

### Option B: Ethernet

Just plug in the cable. It will get an IP automatically via DHCP.

---

## Step 2: Find the New IP Address

From the server (if you have a monitor attached):
```bash
ip a | grep inet
```

Look for something like `192.168.X.X` (not 127.0.0.1)

**Or** check your router's admin page for connected devices / DHCP leases.

**Or** if avahi is working:
```bash
ping printserver.local
```

---

## Step 3: Verify Server is Running

From any computer on the same network:

```bash
curl http://<NEW-IP>:5001/v1/health
```

Should return: `{"status":"ok"}`

Check printer:
```bash
curl http://<NEW-IP>:5001/v1/status
```

Should show Brother QL-720NW as "ready"

---

## Step 4: Update BruFLOW

Change the print server URL in BruFLOW from the old IP to the new IP:

```
Old: http://192.168.30.236:5001
New: http://<NEW-IP>:5001
```

---

## Step 5: Test Print

From BruFLOW, try printing a label.

Or from command line:
```bash
curl -X POST -F "file=@test.png" http://<NEW-IP>:5001/v1/print/label
```

---

## Optional: Set Static IP

So the IP never changes (recommended for production):

### Method 1: On the Server

```bash
sudo nmtui
```

1. Select **"Edit a connection"**
2. Select your connection (WiFi or Ethernet)
3. Change IPv4 Configuration from **"Automatic"** to **"Manual"**
4. Select **"Show"** next to IPv4
5. Add:
   - Addresses: `192.168.1.100/24` (pick IP outside router's DHCP range)
   - Gateway: `192.168.1.1` (your router's IP)
   - DNS servers: `8.8.8.8`
6. OK → Back → Quit
7. Reconnect to apply:
   ```bash
   sudo nmcli connection down "connection-name"
   sudo nmcli connection up "connection-name"
   ```

### Method 2: Router DHCP Reservation (Easier)

1. Log into router admin page
2. Find DHCP settings / Address Reservation
3. Find the print server by MAC address
4. Assign it a fixed IP
5. Reboot server or renew DHCP lease

---

## Troubleshooting

### Can't connect to WiFi
```bash
# List available networks
nmcli device wifi list

# Connect manually
sudo nmcli device wifi connect "NetworkName" password "YourPassword"
```

### Server not responding
```bash
# Check if Docker is running
sudo docker ps

# If container isn't running, start it
cd ~/print-server
sudo docker compose -f docker/docker-compose.prod.yaml up -d
```

### Printer not working
```bash
# Check USB connection
lsusb | grep Brother

# Check device permissions
ls -la /dev/usb/lp0
sudo chmod 666 /dev/usb/lp0

# Restart container
sudo docker compose -f docker/docker-compose.prod.yaml restart
```

### Forgot server password
If you set up the server, the password is what you chose during Debian install.

---

## Quick Reference

| Task | Command |
|------|---------|
| SSH to server | `ssh brutek@<IP>` |
| Find IP | `ip a \| grep inet` |
| WiFi setup | `sudo nmtui` |
| Health check | `curl http://<IP>:5001/v1/health` |
| Printer status | `curl http://<IP>:5001/v1/status` |
| View logs | `sudo docker logs docker-print-server-1` |
| Restart server | `sudo docker compose -f docker/docker-compose.prod.yaml restart` |

---

## Endpoints for BruFLOW

| Purpose | URL |
|---------|-----|
| Health check | `GET http://<IP>:5001/v1/health` |
| Printer status | `GET http://<IP>:5001/v1/status` |
| Print label | `POST http://<IP>:5001/v1/print/label` |
| Print document | `POST http://<IP>:5001/v1/print/document` |
| Check job | `GET http://<IP>:5001/v1/job/{job_id}` |
