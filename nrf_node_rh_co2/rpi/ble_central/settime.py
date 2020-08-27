#!/usr/bin/env python3

'''
single-purpose script, attach to BLE device, send 4 bytes of current time
on the
`XX` as one byte on the
5432 characteristic, disconnect.

0000xxxx-bee5-bee5-NNNN-bee5bee5bee5
NNNN=0x0002
xxxx=0x3001

'''
import bluepy.btle as btle
import struct
import time
import argparse
import struct

HO_TIME_SVC          = "00001001-bee5-bee5-0002-bee5bee5bee5"
HO_TIME_SET_CHAR     = "00003001-bee5-bee5-0002-bee5bee5bee5"


if __name__ == "__main__": #noqa
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--addr', required=True,
                        help="address of the BLE peripheral with NRF LEDBUTTON service")
    parser.add_argument('-v', '--verb', action='store_true')
    parser.add_argument('-i', '--imax', type=int, default=5)
    parser.add_argument('-o', '--logfile', type=str, default=None,
                        help="path to logfile. If None, no data written.")
    args = parser.parse_args()

    addr_type = btle.ADDR_TYPE_PUBLIC
    addr_type = btle.ADDR_TYPE_RANDOM

    print("Connecting to: {}, address type: {}".format(args.addr, addr_type))
    conn = btle.Peripheral(args.addr, addr_type)
    time.sleep(0.5)

    svc = conn.getServiceByUUID(HO_TIME_SVC)
    #TODO: error handling!
    # we can look at the characteristics offered with this service
    _all_crs = svc.getCharacteristics()
    settime_crs = None
    for _c in _all_crs:
        print("{} {} {}".format(_c.propertiesToString(), _c.uuid.getCommonName(),  _c.valHandle))
        if _c.uuid.getCommonName() == HO_TIME_SET_CHAR:
            print("[I] we found the time setter.", _c, _c.valHandle)
            settime_crs = _c

    time.sleep(0.5)
    now  = int(time.time())
    msg = struct.pack("<I", now);
    print("[I] will transmit '{}' ({}by) to val {}".format(msg, len(msg), settime_crs.valHandle))


    #if args.switch_on:
    conn.writeCharacteristic(settime_crs.valHandle, msg);
                             #struct.pack("<I", ))
    #else:
    #    conn.writeCharacteristic(tggle_crs.valHandle,
    #                         struct.pack("<b", 0x00))

    time.sleep(0.5)
    conn.disconnect()
