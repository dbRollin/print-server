# CLI Cheatsheet

Commands used for server setup, deployment, and management. Useful for any Linux CLI project.

---

## SSH / Remote Connection

```bash
# Connect to server
ssh user@192.168.x.x
ssh user@hostname.local

# Copy files to server
scp file.txt user@192.168.x.x:~/
scp -r folder/ user@192.168.x.x:~/

# Copy files from server
scp user@192.168.x.x:~/file.txt ./
```

---

## Package Management (Debian/Ubuntu)

```bash
# Update package lists
sudo apt update

# Upgrade installed packages
sudo apt upgrade -y

# Install packages
sudo apt install -y curl git htop nano

# Search for packages
apt search keyword

# Remove package
sudo apt remove package-name
```

---

## Docker

```bash
# List running containers
sudo docker ps

# List all containers (including stopped)
sudo docker ps -a

# View container logs
sudo docker logs container-name
sudo docker logs container-name --tail 50
sudo docker logs container-name -f              # Follow live

# Start/stop/restart container
sudo docker start container-name
sudo docker stop container-name
sudo docker restart container-name

# Build and run with docker-compose
sudo docker compose -f docker-compose.yaml up -d --build
sudo docker compose -f docker-compose.yaml down
sudo docker compose -f docker-compose.yaml restart

# Enter container shell
sudo docker exec -it container-name /bin/bash

# Remove container
sudo docker rm container-name

# Remove image
sudo docker rmi image-name

# Clean up unused images/containers
sudo docker system prune
```

---

## Git

```bash
# Clone repository
git clone https://github.com/user/repo.git

# Pull latest changes
git pull

# Check status
git status

# Stage changes
git add .
git add filename

# Commit
git commit -m "Message"

# Push
git push

# View commit history
git log --oneline

# Create and switch branch
git checkout -b branch-name

# Switch branch
git checkout branch-name
```

---

## File Operations

```bash
# List files
ls
ls -la                    # Detailed with hidden files

# Navigate
cd /path/to/dir
cd ~                      # Home directory
cd ..                     # Parent directory

# Create directory
mkdir dirname

# Copy
cp file.txt newfile.txt
cp -r folder/ newfolder/

# Move/rename
mv file.txt newname.txt
mv file.txt /new/location/

# Delete
rm file.txt
rm -rf folder/            # Recursive, force (careful!)

# View file contents
cat filename
cat -n filename           # With line numbers
head -20 filename         # First 20 lines
tail -20 filename         # Last 20 lines
tail -f filename          # Follow live updates

# Edit files
nano filename             # Simple editor
# Ctrl+O = save, Ctrl+X = exit
```

---

## File Content Creation

```bash
# Create file with content (heredoc)
cat > filename.txt << 'EOF'
Content goes here
Multiple lines
EOF

# Append to file
echo "new line" >> filename.txt

# Create empty file
touch filename.txt

# Write single line
echo "content" > filename.txt
```

---

## Searching

```bash
# Find files by name
find /path -name "*.txt"

# Search file contents
grep "pattern" filename
grep -r "pattern" /path/  # Recursive
grep -i "pattern" file    # Case insensitive
grep -n "pattern" file    # Show line numbers

# Find command in history
history | grep keyword
```

---

## Network

```bash
# Show IP addresses
ip a
hostname -I

# Test connectivity
ping hostname
ping 192.168.x.x

# HTTP requests
curl http://localhost:5001/v1/health
curl -X POST -F "file=@image.png" http://localhost:5001/v1/print/label

# Check open ports
sudo ss -tlnp
sudo netstat -tlnp

# DNS lookup
nslookup hostname
```

---

## System Information

```bash
# Disk usage
df -h

# Memory usage
free -h

# Running processes
htop                      # Interactive (if installed)
top                       # Basic
ps aux                    # List all processes

# System info
uname -a
cat /etc/os-release

# Uptime
uptime
```

---

## Services (systemd)

```bash
# Start/stop/restart service
sudo systemctl start service-name
sudo systemctl stop service-name
sudo systemctl restart service-name

# Enable/disable at boot
sudo systemctl enable service-name
sudo systemctl disable service-name

# Check status
sudo systemctl status service-name

# View service logs
sudo journalctl -u service-name
sudo journalctl -u service-name -f   # Follow live
```

---

## USB Devices

```bash
# List USB devices
lsusb

# Check USB device path
ls -la /dev/usb/lp*

# Set permissions
sudo chmod 666 /dev/usb/lp0

# Watch for device connections
dmesg -w

# Recent system messages
dmesg | tail -30
```

---

## Permissions

```bash
# Change file permissions
chmod 644 file.txt        # rw-r--r--
chmod 755 script.sh       # rwxr-xr-x
chmod 666 /dev/usb/lp0    # rw-rw-rw-

# Change owner
sudo chown user:group file.txt

# Add user to group
sudo usermod -aG groupname username
```

---

## Text Processing

```bash
# Remove line from file
sed -i '/pattern/d' filename

# Replace text in file
sed -i 's/old/new/g' filename

# Count lines
wc -l filename

# Sort
sort filename

# Unique lines
sort filename | uniq
```

---

## Useful Shortcuts

```bash
# Previous command
!!

# Previous command with sudo
sudo !!

# Last argument of previous command
!$

# Clear terminal
clear
# or Ctrl+L

# Cancel current command
Ctrl+C

# Exit shell
exit

# Search command history
Ctrl+R
```

---

## Common Patterns

```bash
# Chain commands (run second only if first succeeds)
command1 && command2

# Chain commands (run regardless)
command1; command2

# Pipe output
command1 | command2

# Redirect output to file
command > file.txt        # Overwrite
command >> file.txt       # Append

# Redirect stderr
command 2>&1 | tee log.txt
```
