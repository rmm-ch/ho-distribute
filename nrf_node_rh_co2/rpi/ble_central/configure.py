#!/usr/bin/env python3
import bluepy.btle as btle
import struct
import time
import argparse
import lib_hoble

if __name__ == "__main__": #noqa
    #{{{ cmd-line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--addr', required=True,
                        help="address of the BLE peripheral with NRF LEDBUTTON service")
    parser.add_argument('-v', '--verb', action='store_true')
    parser.add_argument('-c', '--cmd', type=int, default=0)
    parser.add_argument('-r', '--max_retries', type=int, default=3)
    parser.add_argument('-g', '--arg',  default=None)
    parser.add_argument('-o', '--logfile', type=str, default=None,
                        help="path to logfile. If None, no data written.")
    args = parser.parse_args()

    #addr_type = btle.ADDR_TYPE_PUBLIC
    addr_type = btle.ADDR_TYPE_RANDOM
    #}}}
    known_cmd_ix = [0, 1, 2, 3, 4, 5, 6]
    if args.cmd in known_cmd_ix:
        print("[I] will attempt to configure cmd {} (arg {})".format(args.cmd, args.arg))
    else:
        raise RuntimeError("[E] unknown command. {}".format(args.cmd))

    # establish connection
    conn = btle.Peripheral(args.addr, addr_type)
    print("[I] connected to {}".format(args.addr))
    time.sleep(0.2)

    # execute selected configuration command
    if args.cmd == 0:
        # change ext i2c domain. (0 1 3
        #   opt should be in [_HO_I2CDOM_ON, _HO_I2CDOM_OFF, _HO_I2CDOM_TOGGLE]
        opt = lib_hoble._HO_I2CDOM_TOGGLE # default
        if args.arg is not None:
            if type(args.arg) is int:
                opt = args.arg
            elif type(args.arg) is str:
                if args.arg == "on":
                    opt = lib_hoble._HO_I2CDOM_ON
                elif args.arg == "off":
                    opt = lib_hoble._HO_I2CDOM_OFF
                elif args.arg in ["tog", "toggle"]:
                    opt = lib_hoble._HO_I2CDOM_TOGGLE



        if opt in [lib_hoble._HO_I2CDOM_ON, lib_hoble._HO_I2CDOM_OFF, lib_hoble._HO_I2CDOM_TOGGLE]:
            ret = lib_hoble.snsr_cfg_i2cdomain(conn, opt)
            print("[I] sent command {} ({})".format(ret, opt))
        else:
            print("[W] opt nt valid. didn't do it. ")


        pass
    elif args.cmd == 1:
        # set period
        arg8 = lib_hoble.AMM_10_SEC
        ret = lib_hoble.snsr_cfg8_hdc(conn, arg8)
        print("[I] sent command {} ({})".format(ret, arg8))

    elif args.cmd == 2:
        # set interval for sampling HDC
        if args.arg is None:
            raise RuntimeError("[E] need to set argument!.")

        arg16 = args.arg
        # need to select the relevant timer to configure.
        cmd = lib_hoble.HO_CFG_TIMERHDC_INTERVAL
        ret = lib_hoble.snsr_cfg16(conn, cmd, arg16)
        print("[I] sent command {} ({})".format(ret, arg16))
        # for some commands, we also need to select appropriate arguments
        # e.g. for the sensor sampling interval, we should also send AMM
        # value.  It is easier to develop the logic on the hub than to do
        # too much on nrf side.
        #arg8 = lib_hoble.AMM_XX_SEC where XX is the closest(?) to args.arg.
        #ret = lib_hoble.snsr_cfg8_hdc(conn, arg8)

    elif args.cmd == 3:
        # set interval for sampling SCD (this sets both the sampler callback
        # and also the sensor auto meas mode)
        if args.arg is None:
            raise RuntimeError("[E] need to set argument!.")
        if int(args.arg) <2 or int(args.arg) > 1800:
            raise RuntimeError("[E] invalid settting! {}".format(args.arg))

        arg16 = int(args.arg)
        cmd = lib_hoble.HO_CFG_TIMERSCD_INTERVAL
        ret = lib_hoble.snsr_cfg16(conn, cmd, arg16)
        print("[I] sent command {} ({})".format(ret, arg16))

    elif args.cmd == 4:
        # stop the SCD device (not the timer...)
        # to reverse this, we can just re-apply the set interval - as per the
        # device protocol basically.
        if args.arg is not None:
            raise RuntimeError("[E] no arg needed!")

        cmd = lib_hoble.HO_CFG_SCD_STOPSAMP;
        ret = lib_hoble.snsr_cfg0(conn, cmd)
        print("[I] sent command {} ({})".format(ret, "no args"))

    elif args.cmd == 5:
        # try setting the time
        print("[I] setting time.")
        ret = lib_hoble.settime(conn)
        print("[I] sent command {}".format(ret))

    elif args.cmd == 6:
        # try time readback, and compare with local time
        print("[I] readback time.")
        ret = lib_hoble.comparetime(conn)
        print("[I] return value: {}".format(ret))


