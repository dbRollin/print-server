================================================================================
                     PRINT SERVER USB INSTALLER
================================================================================

This folder has everything you need to create a bootable USB and deploy
the print server. Supports both Ubuntu Server and Debian.

FILES:
------
  rufus.exe                    - USB flasher tool

  UBUNTU (if Ubuntu works on your hardware):
  ubuntu-server-24.04.iso      - Ubuntu Server installer
  FLASH-USB.bat                - Flash Ubuntu ISO
  COPY-TO-USB.bat              - Add autoinstall config

  DEBIAN (recommended - more stable installer):
  debian-13.x.x-amd64-netinst.iso - Debian installer (download separately)
  FLASH-USB-DEBIAN.bat         - Flash Debian ISO
  COPY-TO-USB-DEBIAN.bat       - Add preseed config

  SHARED:
  DEPLOY-FROM-HERE.bat         - Deploy from Windows after install

================================================================================
OPTION A: DEBIAN (RECOMMENDED)
================================================================================

Use Debian if Ubuntu installer keeps crashing. Debian's installer is
rock-solid and the print server works identically on both.

DOWNLOAD DEBIAN ISO:
  https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-13.2.0-amd64-netinst.iso

Save to this folder (usb-installer/).

STEPS:
  1. Plug in USB drive (8GB+)
  2. Double-click FLASH-USB-DEBIAN.bat
     - Select USB drive in Rufus
     - Click Start, wait ~3 min
  3. Double-click COPY-TO-USB-DEBIAN.bat
     - Adds preseed.cfg for automated install
  4. Eject USB, boot server from it
  5. Installation runs automatically (~10-15 min)
  6. After reboot: admin / printserver

================================================================================
OPTION B: UBUNTU
================================================================================

If Ubuntu works on your hardware, it's also fine.

STEPS:
  1. Plug in USB drive (8GB+)
  2. Double-click FLASH-USB.bat
  3. Double-click COPY-TO-USB.bat
  4. Eject USB, boot server from it
  5. Installation runs automatically
  6. After reboot: admin / printserver

================================================================================
AFTER INSTALL (BOTH OPTIONS)
================================================================================

Once the server reboots into the fresh OS:

  Login:    admin
  Password: printserver

Then run the bootstrap script to install Docker and the print server:

  cd /deployment-kit
  sudo bash bootstrap.sh

Or from this Windows PC, run DEPLOY-FROM-HERE.bat to do it over SSH.

================================================================================
MANAGEMENT AFTER SETUP
================================================================================

  Print API:  http://printserver:5001/v1/
  Portainer:  http://printserver:9000  (container management)
  Cockpit:    https://printserver:9090 (system management)
  CUPS:       http://printserver:631   (document printer)

================================================================================
