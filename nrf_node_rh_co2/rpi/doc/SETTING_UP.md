# Objective: get bluetooth library installed, and adapter configured

* install libbluetooth, python3-bluez
* modify the service to run in experimental mode
* install gattlib
* test example

## installation of bluetooth libraries
 
```
sudo apt update
sudo apt autoremove
sudo apt install libusb-dev libdbus-1-dev libglib2.0-dev libudev-dev libical-dev libreadline-dev
sudo apt install bluez python-bluez python3-bluez
sudo apt install python-dbus

sudo pip3 install bluepy
sudo pip install bluepy

```


## check status, modify as necessary
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

## GATT services : gattlib

The bluetooth connections (at least in python) need gatt to be installed.


We also need gattlib, which depends on boost for the installation.

```
sudo apt-get install libbluetooth-dev python-dev libglib2.0-dev libboost-python-dev libboost-thread-dev

sudo pip3 install gattlib
```

## test example

First, build the examples/ble_peripheral/ble_app_blinky firmware, and 
transfer it onto the nrf52. Reset it.

Find the address of the nrf device, e.g. with nordic app, or better
on the command line of the RPi (this way we know we can see the device)

```
bluetoothctl
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



