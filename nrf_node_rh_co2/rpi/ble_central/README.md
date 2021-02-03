

# Overview of files

**ble_ho_snsr.py**

- main tool to connect to a nRF sensor board, collect sampled data and
  log to files.  

Usage
    python3 ble_ho_snsr.py --addr <BLE address> --conv_incoming --logdir <path to write files>

    note: if the path does not exist, it will be created. Currently no permissions checked!

**configure.py**

- tool that does various simple interactions in one-shot usage, such as
  changing sampling rates, setting nRF time. 

Usage
    python3 configure.py --addr <BLE address> --cmd <cmdno> --arg <opt>

    Some commands require an argument, others do not, see notes below.


  --cmd 0  <opt>  update the state of the external sensors
        <opt=0> switch on
        <opt=1> switch off
        <opt=3> toggle

  --cmd 1 <opt> update the sampling period of the HDC2010 on-board sensor
        <opt> in [0x00, 0x07], see HDC data sheet for details.
        0: off 1: 120s 2: 60s 3: 10s 4: 5s 5: 1s 6: 2Hz 7: 5Hz

  --cmd 2 <opt> update sampling setting #TODO: what are the valid options?

  --cmd 3 <opt> update the sampling period of the SCD30 CO2 sensor
        <opt> in [2, 1800] corresponding to interval in seconds.

  --cmd 4       stop the SCD30 device.

  --cmd 5       set the time on the nRF device (send host time)

  --cmd 6       read the time on the nRF device and compare to host time.

    
    
one-shot script 

**`lib_hoble.py`**

- A library that defines a handful of connection utility functions, including
  time set/get, configuration of sensor rates, and BLE characteristic 
  inspection. Also defines constants and UUIDs relevant for the nRF tag.


## Obselete
**gettime.py**

- Obselete: use `configure.py --addr <BLE address> --cmd 6` instead

- single-purpose script to read the internal RTC time of a
  MOBOTS nRF wireless sensor node.
  Retrieves and reports the nRF time, also compares local time on host, and
  reports the difference.

    Usage: python3 gettime.py --addr <BLE address>     

**settime.py**

- Obselete: use `configure.py --addr <BLE address> --cmd 5` instead

- single-purpose script to set the internal RTC time of a
  MOBOTS nRF wireless sensor node.  Sends the current time of the host
  (as a little-endian, 4-byte unsigned integer).

    Usage: python3 gettime.py --addr <BLE address>     


## Dependencies 

bluepy.btle

builtin libraries available since py3 (many older)
- argparse, struct, time, datetime, os, errno

