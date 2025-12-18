# Automated Ubuntu Install

This folder contains files for hands-off Ubuntu Server installation.

## Quick Start

1. Download Ubuntu Server 24.04 LTS ISO
2. Create bootable USB with Rufus (or dd)
3. Mount the USB and add the autoinstall config
4. Boot target machine from USB
5. Walk away - it installs automatically

## Adding Autoinstall to USB

After creating the bootable USB:

### Option A: Add to existing USB (easier)

1. Mount the USB drive
2. Create folder: `<USB>/autoinstall/`
3. Copy `autoinstall.yaml` to `<USB>/autoinstall/user-data`
4. Create empty file: `<USB>/autoinstall/meta-data`

### Option B: Modify GRUB (more reliable)

1. Mount USB, edit `boot/grub/grub.cfg`
2. Find the "Install Ubuntu Server" menu entry
3. Add to the linux line: `autoinstall ds=nocloud;s=/cdrom/autoinstall/`
4. Create `autoinstall/` folder with files as above

## Default Credentials

**Change these immediately after install!**

- Username: `print`
- Password: `printserver`
- Hostname: `printserver`

## After Install

1. SSH in: `ssh print@printserver.local`
2. Change password: `passwd`
3. Run setup: `./setup-print-server.sh`
4. Log out and back in (for Docker group)
5. Clone repo and configure

## Customizing

Edit `autoinstall.yaml` to change:
- `identity.hostname` - Machine name
- `identity.username` - User account
- `identity.password` - Password hash (generate with `mkpasswd -m sha-512`)
- `network` - Static IP instead of DHCP

## Generate Password Hash

On a Linux system:
```bash
mkpasswd -m sha-512
```

Or with Python:
```python
import crypt
print(crypt.crypt("yourpassword", crypt.mksalt(crypt.METHOD_SHA512)))
```
