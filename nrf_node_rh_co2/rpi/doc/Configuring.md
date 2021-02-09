# Preparing a RPi without a screen


# A. Prepare the SD card

## 1. Get the OS image

Raspberry pi O/S main [downloads page](https://www.raspberrypi.org/downloads/raspbian/) shows three images:

* lite
* with desktop (lite + GUI)
* with desktop and recommended software (lite + GUI plus many packages)

We are doing without a screen, so the assumption is that we won't (ever?) attach a screen.  Let's use the lite version.

Download image from this link (or use wget or curl etc):
[Raspbian buster lite](https://downloads.raspberrypi.org/raspbian_lite_latest)


    $ cd ~/Downloads && wget -O raspbian_lite_latest.zip https://downloads.raspberrypi.org/raspbian_lite_latest
    
    # Verify checksum
    $ sha256sum raspbian_lite_latest.zip > rpi_lite.checksum
    $ echo "12ae6e17bf95b6ba83beca61e7394e7411b45eba7e6a520f434b0748ea7370e8" > reference.checksum
    $ diff rpi_lite.checksum reference.checksum
    # should have no output. hmm except that the first one has a filename. 
    # remove by hand and diff again => ok now.
    

### 1.1. convert lite (headless) to desktop (GUI version)
sidenote: If necessary, installing this meta-package will turn lite into desktop 

    sudo apt-get install raspberrypi-ui-mods


## 2. install balena etcher

Linux: 
Note - version 1.5.51 is in ubuntu 18.04 repositories

    $ sudo apt-get install balena-etcher-electron

Windows:
    
Download the [installer](https://github.com/balena-io/etcher/releases/download/v1.5.50/balenaEtcher-Setup-1.5.50.exe) and run it.

## 3. Use etcher to install image onto SD card

* Insert micro-SD media into PC
* Launch tool
* Select ~/Downloads/raspbian_lite_latest.zip
* Check the micro-SD media is the correct one.
* press `Flash`, type su password (linux at least) 
* wait for the flash and verify stages (approx 3 mins)

## 4. Modify the settings to enable external connections

We will set up external peripherals, and prepare the connection for the wifi.

### 4.1 SSH

* insert the micro-SD card into your PC
* find the `boot` partition of the SD card
* make a backup of the files we will change
    * config.txt 
    * cmdline.txt

* edit config.txt   
    * add `dtoverlay=dwc2` to the section `[all]`, at the very end of the file 

* create an empty file called `ssh`.

* edit cmdline.txt
    * add `modules-load=dwc2,g_ether` after `rootwait`.

For me, this sequence is ok

    $ cd /media/rmm/boot
    # backups
    $ cp -p config.txt config.orig 
    $ cp -p cmdline.txt cmdline.orig
    # edits
    $ echo "dtoverlay=dwc2" >> config.txt
    $ touch ssh
    $ sed -i 's/\<rootwait\>/& modules-load=dwc2,g_ether/' cmdline.txt

**Now we can log in to the RPi over a network**
(need to put sd card into the RPi, boot, wait 120s, then...)

    $ ssh pi@raspberrypi.local
    # default password is `raspberry`
    # other commands as needed
    $ sudo shutdown now

Can also use putty or other ssh-ready tool


### 4.2. Wifi

    

This file needs to be placed in `/media/rmm/boot`, and edited to reflect correct parameters for ssid/psk.  
Contents of [`conf/wpa_supplicant.conf`](../conf/wpa_supplicant.conf):
```
country=CH
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="the name of your wifi network"
    psk="the wifi password in plain text here..."
}
```

    $ cd /media/rmm/boot
    $ cp <REPO_ROOT>/rpi/conf/wpa_supplicant.conf .
    $ edit wpa_supplicant.conf


### 4.3 wifi setup on windows side

Follow instructions here: [Apple bonjour service](https://support.apple.com/kb/DL999?locale=en_US)

Most variants of linux and macOS have mDNS or bonjour services running by default.

RPi broadcasts the hostname to the network, and mDNS allows a PC (or other device) to remotely connect without knowing the IP address.

    $ ssh pi@raspberrypi.local
    # default password `raspberry`
    # port 22
    # user `pi`



# B. Setup on the rpi, once running

## 1. Configuration

Enter the configuration tool:

    $ sudo raspi-config
    
* **menu 1**: change password (also not essential, but good idea if accessible
  over wifi.  Record it somewhere!)
* **menu 2/N1**: change hostname (not essential but on EPFL networks we are likely to have >1 RPi, so they will clash and mDNS stops working).
* **menu 5/P5** enable I2C (optional)
* **menu 5/P7** enable 1-wire interface (optional)


Note: all of these configurations could be managed through `config.txt`, but
the interactive tool is simpler, at least for a first go. See
[docs](https://www.raspberrypi.org/documentation/configuration/config-txt/README.md).

## 2. Update packages

The operating system, rasbpian, is based on debian.  This uses a package manager to keep libraries up to date, and to install new ones.  

    # get latest listing of packages
    $ sudo apt update
    # install latest version of each package that is already installed
    $ sudo apt upgrade

Installing a new one is straightforward:

    $ sudo apt install screen

Multiple packages can be installed together:

    $ sudo apt install git build-essential



## 3. SSH keys

TODO - setup ssh keys for passwordless access and scp.

----

----

These instructions tested on RPi 4B and RPi 3B v1.2.

# C. Some references

* [tutorial rasbpian installation](https://itsfoss.com/tutorial-how-to-install-raspberry-pi-os-raspbian-wheezy/)

* [forum on differences between lite/desktop](https://www.raspberrypi.org/forums/viewtopic.php?t=204204)

* [tutorial headless setup 1](https://tutorial.cytron.io/2017/05/02/getting-started-raspberry-pi-zero-w/)

* [tutorial headless /wifi setup 2](https://desertbot.io/blog/headless-raspberry-pi-3-bplus-ssh-wifi-setup)

* [doc headless / wifi setup 3](https://www.raspberrypi.org/documentation/configuration/wireless/headless.md)

* [Looks interesting - gpio read/write via browser](https://github.com/projectweekend/Pi-GPIO-Server)
