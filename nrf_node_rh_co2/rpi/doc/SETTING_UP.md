# Objective: get bluetooth library installed, and adapter configured

1. [Install](#1-installation-of-bluetooth-libraries) libbluetooth, python3-bluez
2. Modify the bluetooth service to run in [experimental mode](#2-check-bluetooth-service-status-modify-as-necessary)
3. Install [gattlib](#3-gatt-services--gattlib)
4. [Test](#4-testing) an example connecting the linux-like host to a BLE central node.

## 1. installation of bluetooth libraries
 
```
sudo apt update
sudo apt autoremove
sudo apt install libusb-dev libdbus-1-dev libglib2.0-dev libudev-dev libical-dev libreadline-dev
# note: approx 1m30 on RPi 3B

sudo apt install bluez python3-bluez


```

Some steps that are likely unnecessary (excluded in 2021 installation):

sudo apt install python-dbus python-bluez bluepy


## 2. check bluetooth service status, modify as necessary
```
sudo service bluetooth status
rfkill list

> 0: phy0: Wireless LAN
>     Soft blocked: no
>     Hard blocked: no
> 1: hci0: Bluetooth
>     Soft blocked: no
>     Hard blocked: no

# we are looking for hciX, (probably hci0), and checkign whether it
# states blocked: yes, then we need to unblock it:

sudo rfkill unblock 1
# where 1 refers to the index before hci0 above.
```
Now we have enabled the adapter for bt/ble. Let us check the mode it runs in.

``` 
sudo service bluetooth status
ps aux | grep bluetoothd
>root       618  0.0  0.2   9808  4348 ?        Ss   20:10   0:00 /usr/lib/bluetooth/bluetoothd -C

# it is in -C (compat) mode, but not -E (experimental)

# now set up the experimental bt

sudo nano /lib/systemd/system/bluetooth.service
# change 
ExecStart=/usr/lib/bluetooth/bluetoothd 
# to 
ExecStart=/usr/lib/bluetooth/bluetoothd -C --experimental

# and now restart the service
sudo systemctl daemon-reload
sudo systemctl restart bluetooth

# and recheck
ps aux | grep bluetoothd
> root     22998  0.0  0.2   9940  4496 ?        Ss   20:13   0:00 /usr/lib/bluetooth/bluetoothd -C --experimental

# we have --experimental running

```

## 3. GATT services : gattlib

The bluetooth connections (at least in python) need gatt to be installed.


We also need gattlib, which depends on boost for the installation.

```
sudo apt-get install libbluetooth-dev python-dev libglib2.0-dev libboost-python-dev libboost-thread-dev

sudo pip3 install gattlib
# note: approx 2m30 on RPi 3B

```

## 4. Testing

### Test example -- nordic example repository:

First, build the examples/ble_peripheral/ble_app_blinky firmware, and 
transfer it onto the nrf52. Reset it.

Find the address of the nrf device, e.g. with nordic app, or better
on the command line of the RPi (this way we know we can see the device)

Note: invoking a scan within `bluetoothctl` might require root permissions, depending on your 
operating system.  Do this with `sudo bluetoothctl`.

```
$ bluetoothctl

>Agent registered
[bluetooth]# scan on
>Discovery started
[CHG] Controller DC:A6:32:05:B1:B9 Discovering: yes
[NEW] Device E9:E6:09:7C:78:21 Nordic_Blinky
[NEW] Device 40:AF:7B:F7:4E:60 40-AF-7B-F7-4E-60
[NEW] Device 58:89:31:33:AF:B7 58-89-31-33-AF-B7
[NEW] Device 7C:AB:AD:1C:CE:FA 7C-AB-AD-1C-CE-FA

#<output like this continues...>
[bluetooth]# scan off
>Discovery stopped

```
The device we wanted is the one named `Nordic_Blinky`

The example central device code will connect to that peripheral, and
subscribe to the button info characteristic.

If the button is pressed (or unpressed) while the connection is open,
this should be reported.  Periodically, the LED will be toggled via
writing to the relevant characteristic.

    python3 ble_ledbutton_service.py --addr E9:E6:09:7C:78:21


### Test connectivity -- mobots H/O device

If you have a hiveopolis device (or prototype with equivalent interface), 
then we look for a name like *T_RH-CO2alpha7*.

It is possible either using the `bluetoothctl` procedure as above, or 
alternatively try  a tool in this repository:


```
$ sudo python3 scn.py

Discovered device 4c:eb:bd:2d:c4:a0
Discovered device e5:26:db:47:13:66
Discovered device b0:c5:54:4b:34:b2
...

[I] scanning for MOBOTS tags
   Device a2:77:33:47:b8:54 (random), RSSI=-59 dB. t3: 0000180a-0000-1000-8000-00805f9b34fb
    Appearance = 0000
    Flags = 06
    Complete 16b Services = 0000180a-0000-1000-8000-00805f9b34fb
    Complete Local Name = T_RH-CO2alpha7
[I] found 1 MOBOTS tags
    ['A2:77:33:47:B8:54']

```
Here we see one device that advertising the service matching our expectation, and can 
proceed with this address.

```
# simply write out the address each time
python3 ble_ho_snsr.py --addr A2:77:33:47:B8:54 -ci -v 

# or for convenience, use an environment variable:
export TAG=A2:77:33:47:B8:54

python3 gettime.py --addr ${TAG}
python3 settime.py --addr ${TAG}

python3 ble_ho_snsr.py --addr ${TAG} -ci -v 

```
For more information on the various commands in the `ble_central` directory, check the [readme](../ble_central/README.md).







