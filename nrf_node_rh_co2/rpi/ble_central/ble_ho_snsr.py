#!/usr/bin/env python3
#{{{ notes
'''
seemingly working example here. borrows a lot from the bluepy example docs

https://ianharvey.github.io/bluepy-doc/notifications.html

behaviour:
    - attempts to connect to the ble device with address given in command-line argument
    - optionally displays list of all characteristics
    - attempts to establish connection to service NRF LEDBUTTON
    - subscribes to notifications on the button characteristic
    - periodically writes to the LED characteristic, to toggle it.

Very little error handling! If you quit early, you have to call
conn.disconnect() manually.  If your nrf52 is not running the LEDBUTTON
service, it will die ungracefully. If you leave this BLE central attached to
the peripheral, and the program does not exit correctly, no other device will
be able to connect to the peripheral. (A reset on the nrf52 board will be fine
to put it back into advertising phase)


note: to view incoming data,
- if they encode strings :    txt = msg.decode('utf8')
- if they encode binary data: dat = bytearray(msg)
   and then to print we can use
   txt_of_dat = "".join(["{:02x}".format(b) for b in dat])

- data is logged one sample per line. the format can be raw binary (with
  --log_format 1) or human-readable floats (with --log_format 2)

'''
#}}}
import bluepy.btle as btle
import struct
import time
import datetime
import argparse, os.path
import os, errno

import copy

from lib_hoble import (conv_scd_from_bytes, str_scd_from_bytes,
                       bytes_to_u32, bytes_to_u16,
                       conv_hdc_from_bytes,
                       conv_bat_from_bytes,
                       )

'''
TODO logformat updating

- tidy up the mess of repeated funcs in libraries
- write headers (depending on file types)
- variable ordering in conv_hdc_from_bytes --> avoid having to invert after
  using the function

- what is possible to move to lib only:
  - verify usage of all functions in this tool
  - verify usage of all UUIDs





'''

#{{{ mkdir_p
def mkdir_p(path):
    '''
    emulate 'mkdir -p' -
     create dir recursively; if the path exists, don't error
    '''
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise
#}}}

REPORT_IVAL = 30 # sec. Just indicates "Waiting...<sec elap> | <hh:mm:ss>

#{{{ UUID definitions
#LBS_UUID_SERVICE     = "00001523-1212-efde-1523-785feabcd123"
#`00006001-bee5-bee5-0001-bee5bee5bee5
#HO_SNSR_THCO2_UUID_DATA_RAW

'''
  #define HO_SNSR_THCO2_UUID_SERVICE      0x5001
  #define HO_SNSR_THCO2_UUID_DATA_RAW     0x6001
  //#define HO_SNSR_THCO2_UUID_HDC_DATA_RAW 0x6011
  //#define HO_SNSR_THCO2_UUID_SCD_DATA_RAW 0x6021
  #define HO_SNSR_THCO2_UUID_DATA_FMT     0x6101
  #define HO_SNSR_THCO2_UUID_HDC_DATA_FMT 0x6111
  #define HO_SNSR_THCO2_UUID_SCD_DATA_FMT 0x6121
  #define HO_SNSR_THCO2_UUID_HDC_CFG      0x7011
  #define HO_SNSR_THCO2_UUID_SCD_CFG      0x7021

'''
HO_SNSR_SVC          = "00005001-bee5-bee5-0001-bee5bee5bee5"
HO_SNSR_CHR_DATA_RAW = "00006001-bee5-bee5-0001-bee5bee5bee5"
HO_SNSR_CHR_DATA_FMT = "00006101-bee5-bee5-0001-bee5bee5bee5"
HO_SNSR_THCO2_UUID_SCD_DATA_RAW = "00006021-bee5-bee5-0001-bee5bee5bee5"

HO_TIME_SVC          = "00001001-bee5-bee5-0002-bee5bee5bee5"
HO_TIME_SET_CHAR     = "00003001-bee5-bee5-0002-bee5bee5bee5"
HO_SYS_BATLVL_CHAR   = "00005005-bee5-bee5-0002-bee5bee5bee5"
#HO_SYS_UUID_BATTERY_LEVEL 0x5005
#HO_bat 00005005-bee5-bee5-0002-bee5bee5bee5
#}}}

# {{{ converters
# - note: these are all in lib_hoble now
def conv_hdc_T_from_bytes(bytestr):
    # py3 only!
    B = bytes.fromhex(bytestr)
    u16Temp = B[0] | B[1] <<8
    # conversion in C code with 1000x for faking floating point.
    # ((u16T * 165 * 1000) / 65536.) - 40000
    f_temp = ((u16Temp * 165 * 1.) / 65536.) - 40
    return f_temp

def conv_hdc_RH_from_bytes(bytestr):
    #
    B = bytes.fromhex(bytestr)
    u16Hum = B[2] | B[3] << 8
    f_hum_pct = (u16Hum * 100.0) / 65536;

    return f_hum_pct

def conv_hdc_ts_from_bytes(bytestr):
    B = bytes.fromhex(bytestr)
    u32_ts = B[4] | B[5] << 8 | B[6] << 16 | B[7] << 24;
    return u32_ts

def conv_hdc_utc_from_bytes(bytestr):
    B = bytes.fromhex(bytestr)
    u32_time_s = B[8] | B[9] << 8 | B[10] << 16 | B[11] << 24;
    return (u32_time_s)


# }}}

#{{{ conversion of received data to readable


def fmt_time(time_s, fmt='%H:%M:%S'):
    return datetime.datetime.fromtimestamp(time_s).strftime('%H:%M:%S')

def str_bat_from_bytes(bytestr):
    (time_s, v_bat, v_vdd) = conv_bat_from_bytes(bytestr)
    s = "{}  Vbat {:.3f} Vdd {:.3f}".format(
        fmt_time(time_s), v_bat, v_vdd)
    return s
    #


def str_hdc_from_bytes(bytestr):
    (f_temp, f_hum_pct, f_timestep, utime_s) = conv_hdc_from_bytes(bytestr)
    s = "{}  {:+5.3f}oC {:.2f}%RH".format(
        fmt_time(utime_s), f_temp, f_hum_pct)
        #fmt_time(f_timestep), f_temp, f_hum_pct)
    return s


# }}}

# {{{ verbose displays
def disp_descriptors(conn, addr):
        print("[D] all descriptors associated with device {}".format(args.addr))
        print("===="*12)
        d = conn.getDescriptors()
        for _ in d:
            print("   {}".format(str(_)))

def disp_chars(conn, addr):
        print("[D] all characteristics associated with device {}".format(addr))
        print("===="*12)
        crs = conn.getCharacteristics()
        for _ in crs:
            print("   {}".format(str(_)))

        print("===="*12)
# }}}

#{{{ connection lookup
def lookup_crs(svc, TGT_UUID, lbl=""):
    # we can look at the characteristics offered with this service
    _all_crs = svc.getCharacteristics()
    tgt_crs = None
    print("===== checking chars in the service {} =====".format(svc.uuid.getCommonName()))
    print("    {:7} {:36}  {}".format("handle", "uuid", "properties"))
    print("    {:7} {:36}  {}".format("------", "----", "----------"))

    for _c in _all_crs:
        print("    {:7} {:36}  {}".format(_c.valHandle, _c.uuid.getCommonName(),
            _c.propertiesToString() ))
        if _c.uuid.getCommonName() == TGT_UUID:
            tgt_crs = _c
    if tgt_crs is not None:
        print("[I] we found the '{}' characteristic (handle {}| 0x{:02x}).".format(
            lbl, tgt_crs.valHandle, tgt_crs.valHandle))
        print("=" * 64)
    return tgt_crs
#}}}

def dump_log_line(logfile, line, prefix="#", echo=True):
    if echo:
        print(line)

    pre2 = "{:.3f}|".format(time.time())
    if logfile is not None:
        with(open(logfile, "a")) as lf:
            lf.write("{}{}{}\n".format(prefix, pre2, line))

# define a delegate to keep track of incoming notifications
# (the async handling is provided by the pybluez library already.
#{{{ class MulitPartReaderDgt
class MulitPartReaderDgt(btle.DefaultDelegate):
    '''
    simple notify receive delegate, anticipating chained messages. Aim to
    put all elements together that correspond to a single message, between
    the characters defined in `start`/`end` args.
    '''
    def __init__(self, exptlbl, start="$", end="*", logdir=None, handle_map={},
                 verb=0, conv_inc=False, logfmt=2):
        #handles=[]):
        btle.DefaultDelegate.__init__(self)
        # ... initialise here
        # nothing special to do I guess.
        self.recv_msgs    = 0
        self.recv_byte    = 0
        self._last_msg    = ""
        self._last_info   = ""
        self.start_char   = start
        self.end_char     = end
        self.logdir       = logdir
        self.exptlbl      = exptlbl
        self._recent_msgs = []
        self._shadow_msgs = []
        self.expt_handles = handle_map
        self.verb         = verb
        self.conv_inc     = conv_inc
        self._last_multipart = ""
        self.logfmt       = logfmt # 1=legacy, binary strings 2=csv human readable


        self.setup_logdir()

    def setup_logdir(self):
        # defaults
        self.logf_hdc     = None
        self.logf_scd     = None
        self.logf_bat     = None

        if self.logdir is not None:
            mkdir_p(self.logdir)

            if not os.path.exists(self.logdir):
                raise RuntimeError("[F] could not create logdir {} ".format(self.logdir));

            # select log stub
            now = datetime.datetime.now()
            # TODO: rmm update log formatting/log handling here Wed 17 Feb 2021 10:26:48 CET
            self._logstub = "{}_{}".format(now.strftime("%y%m%d"), self.exptlbl)

            #self.logf_sys = os.path.join(self.logdir, "{}.{}".format(self._logstub, "syslog"))
            suffix = ""
            if self.logfmt == 2:
                suffix = ".csv"
            self.logf_bat = os.path.join(self.logdir, "{}.{}{}".format(self._logstub, "batlvl", suffix))
            self.logf_scd = os.path.join(self.logdir, "{}.{}{}".format(self._logstub, "datscd", suffix))
            self.logf_hdc = os.path.join(self.logdir, "{}.{}{}".format(self._logstub, "dathdc", suffix))

            if self.logfmt == 2:
                # write a header for each of the log files
                # slightly clunky setup - better to loop?
                with open(self.logf_scd, "w") as f:
                    cols = ["timestamp", "seq", "CO2", "T", "RH"]
                    hdr = ",".join(cols)
                    f.write(hdr + "\n")
                with open(self.logf_bat, "w") as f:
                    cols = ["timestamp", "Vbat", "Vdd"]
                    hdr = ",".join(cols)
                    f.write(hdr + "\n")
                with open(self.logf_hdc, "w") as f:
                    cols = ["timestamp", "T", "RH", "seq"]
                    hdr = ",".join(cols)
                    f.write(hdr + "\n")





    #{{{ merging multi-parts
    def test_mergable(self):
        i0 = None
        i1 = None
        i=0
        print("D-1: input list {} / type {}".format(len(self._recent_msgs), type(self._recent_msgs) ))
        self._shadow_msgs = copy.deepcopy(self._recent_msgs)
        #self._shadow_msgs = list(self._recent_msgs) # make a copy so it doesn't change under our feet
        print("D-2: input list {} / type {}".format(len(self._recent_msgs), type(self._recent_msgs) ))

        for i, elem in enumerate(self._shadow_msgs):
            print("D0: testing elem {} '{}' for init char {}.".format(i, elem, self.start_char))

            if elem.startswith(self.start_char):
                i0 = i
                break

        if i0 is not None:
            for i, elem in enumerate(self._shadow_msgs, start=i0):
                print("D1: testing elem {} '{}' for end  char {}.".format(i, elem, self.end_char))
                # also need to rstrip "\x00" chars :(
                # newline, \x00 and whitespace
                if elem.rstrip("\n").rstrip("\x00").rstrip().endswith(self.end_char):
                    i1 = i
                    break
        # destroy the shadow since not useful this round
        if i0 is None or i1 is None:
            self._shadow_msgs = []

        print("D-4 we have list {}:{}, elems {} (i{})".format(i0, i1, len(self._shadow_msgs), i))
        return i0, i1

    def try_merge(self):
        i0, i1 = self.test_mergable()
        msg = ""
        tot_l = 0
        if i0 is not None and i1 is not None:
            l = len(self._shadow_msgs)
            print("[D3] got a nice full list to merge. {}:{}. tot:{}".format(i0, i1, l))
            # do a merge, on the shadow list
            l = len(self._shadow_msgs)
            if i1 >= l:
                raise RuntimeError("[E] input list is too short! {} >={})".format(i1, l))

            for i in range(i0, i1+1): # want inclusive range ( [i0, i1] )
                msg += self._shadow_msgs[i].strip()

            tot_l = len(msg)


            if tot_l:
                print("[I] merged {} parts into message of len {} by.".format(i1-i0, tot_l))
                print("\t'{}'".format(msg))

            self._last_multipart = msg

            self._shadow_msgs = [] # consumed now
            self._recent_msgs = []


            # (note this is a bg task and the queue could get corrupted during
            # the merge! don't do popping etc.)
            return tot_l
        else:
            return False
    #}}}

    def handleNotification(self, cHandle, data):
        # ... perhaps check cHandle
        _hname = "unkown"
        if cHandle in self.expt_handles:
            _hname = self.expt_handles.get(cHandle, "key error")
            if self.verb >= 2:
                print("[I] data is from handle {} ({})".format(cHandle, _hname))
        else:
            print("[W] unexpected data received! data is from handle {}".format(cHandle))

        # common processing
        self.recv_msgs += 1
        self.recv_byte += len(data)
        if type(data) is str:
            data = data.encode('utf8')

        thebytes = "".join(["{:02x}".format(b) for b in bytearray(data)])

        short = thebytes[:]
        # handle-specific processing
        if (_hname.startswith("batlvl")):
            lab = "[BAT]"
            if self.conv_inc:
                short = str_bat_from_bytes(thebytes)

            self._last_info3 = "[I-{:5d}] recv [{}] ({}by)".format(
                    self.recv_msgs, short, self.recv_byte)

            print("   ##H{}{} {}".format(cHandle, lab, self._last_info3))
            #print("   ##H{}{} ".format(cHandle, "[BAT]") + self._last_info3)
            #self._recent_msgs.append(thebytes)#.decode('utf-8'))
            if self.logf_bat is not None:
                if self.logfmt == 1:
                    with(open(self.logf_bat, "a")) as lf:
                        lf.write(thebytes + "\n");
                elif self.logfmt == 2:
                    full_row = ",".join([str(e) for e in conv_bat_from_bytes(thebytes)])
                    with(open(self.logf_bat, "a")) as lf:
                        lf.write(full_row + "\n")



        elif (_hname.startswith("SCD")):
            lab = "[SCD]"
            if self.conv_inc:
                short = str_scd_from_bytes(thebytes)

            self._last_info2 = "[I-{:5d}] recv [{}] ({}by)".format(
                    self.recv_msgs, short, self.recv_byte)
            print("   ##H{}{} ".format(cHandle, lab)  + self._last_info2)
            if self.logf_scd is not None:
                if self.logfmt == 1:
                    with(open(self.logf_scd, "a")) as lf:
                        lf.write(thebytes + "\n");
                elif self.logfmt == 2:
                    full_row = ",".join([str(e) for e in conv_scd_from_bytes(thebytes)])

                    with(open(self.logf_scd, "a")) as lf:
                        lf.write(full_row + "\n")

        elif (_hname.startswith("raw/bulk")):
            lab = "[HDC]"
            if self.conv_inc:
                short = str_hdc_from_bytes(thebytes)


            self._last_info = "[I-{:5d}] recv [{}] ({}by)".format(
                    self.recv_msgs, short, self.recv_byte)
            self._last_msg = data
            print("   ##H{}{} ".format(cHandle, lab) + self._last_info)
            if self.logfmt == 1:
                self._recent_msgs.append(thebytes)#.decode('utf-8'))
            elif self.logfmt == 2:
                # here do a reordering - the function returns a non-homogeneous order.
                (f_temp, f_hum_pct, f_timestep, utime_s) = conv_hdc_from_bytes(thebytes)
                full_row = ",".join([str(e) for e in (utime_s, f_temp, f_hum_pct, f_timestep)] )
                self._recent_msgs.append(full_row)








    def write_to_log(self):
        if self.logf_hdc is not None:
            i = 0
            with(open(self.logf_hdc, "a")) as lf:
                while self._recent_msgs:
                    s = self._recent_msgs.pop(0)
                    #print("-->writing {} {} to file".format(i, s))
                    lf.write(s + "\n")
                    i += 1
            #print("[I] wrote {} elems to file {}".format(i, args.logfile))

        # instead of trying to merge, just put into a file.

        #ret = self.try_merge()
        #if ret:
        #    print("[I] assembled message of {} by:\n{}".format(ret, self._last_multipart))
#}}}


#{{{ settime
def settime(conn):
    svc = conn.getServiceByUUID(HO_TIME_SVC)
    settime_crs = lookup_crs(svc, HO_TIME_SET_CHAR, "time setter")
    if settime_crs is not None:
        time.sleep(0.1)
        now  = int(time.time())
        msg = struct.pack("<I", now);
        print("[I] will transmit '{}' ({}by) to val {}".format(msg, len(msg), settime_crs.valHandle))
        conn.writeCharacteristic(settime_crs.valHandle, msg);
        return now

    else:
        print("[W] failed to find time setter char (uuid:{}). Time not set.".format(
        HO_TIME_SET_CHAR))
        return None
#}}}


#{{{ mainloop gathering data
def mainloop(conn, addr, exptlbl, logdir, verb=0, imax=None, sleep_period=0.5,
             conv_inc=False, logfmt=2):

    time.sleep(sleep_period)
    #TODO: implement a handle to disconnect in case of unexpected stop. (atexit?)

    # display some extra information (not super informative, a lot of object
    # mem addresses, but we do get the info on object type at least)
    if verb:
        disp_descriptors(conn, addr)
        disp_chars(conn, addr)

    # now lets connect to the service :
    svc     = conn.getServiceByUUID(HO_SNSR_SVC)
    svc_sys = conn.getServiceByUUID(HO_TIME_SVC)
    #TODO: error handling!

    #data_fmt_crs = lookup_crs(svc, HO_SNSR_CHR_DATA_FMT, "formatted data")
    data_raw_crs = lookup_crs(svc, HO_SNSR_CHR_DATA_RAW, "raw/bulk data")
    scdraw_crs   = lookup_crs(svc, HO_SNSR_THCO2_UUID_SCD_DATA_RAW, "SCD raw data")
    bat_crs      = lookup_crs(svc_sys, HO_SYS_BATLVL_CHAR, "batlvl")
    #data_raw_crs = None
    #bat_crs = None
    #print("[D] hanndle candidates - {} {}".format(data_raw_crs, data_raw_crs.valHandle+1))
    handle_map = {}

    time.sleep(sleep_period)
    if data_raw_crs is not None:
        # subscribe to notifications on the raw/bulk data chrs (handle+1)
        conn.writeCharacteristic(data_raw_crs.valHandle+1, struct.pack('<bb', 0x01, 0x00))
        #handles = [data_raw_crs.valHandle,]
        handle_map[data_raw_crs.valHandle] = "raw/bulk data"
    if scdraw_crs is not None:
        conn.writeCharacteristic(scdraw_crs.valHandle+1, struct.pack('<bb', 0x01, 0x00))
        #handles.append(scdraw_crs.valHandle)
        handle_map[scdraw_crs.valHandle] = "SCD raw data"

    if bat_crs is not None:
        conn.writeCharacteristic(bat_crs.valHandle+1, struct.pack('<bb', 0x01, 0x00))
        #handles.append(bat_crs.valHandle)
        handle_map[bat_crs.valHandle] = "batlvl"


    if len(handle_map) > 0:
        print("[I] subscribed to {} characteristics. Handles: {}".format(
            len(handle_map), " ".join(["{}".format(vh) for vh in handle_map.keys()]) ))
        # attach delegate to handle incoming notifications
        the_dgt = MulitPartReaderDgt(exptlbl=exptlbl, logdir=logdir,
                                     handle_map=handle_map, verb=verb,
                                     conv_inc=conv_inc, logfmt=logfmt)
        conn.withDelegate(the_dgt)
        i= 0
        while True:
            if len(the_dgt._recent_msgs): #> 5:
                the_dgt.write_to_log()
            #else:
            #    print("[D] waiting, {} elems".format(len(the_dgt._recent_msgs)))

            if conn.waitForNotifications(1.): # blocking for 1sec
                #print(str(i) + "[I] recvieved ontify (on what channel/characteristic")
                if verb>=1:
                    pass # no extra screen dumps for now

                continue

            i += 1
            if i % REPORT_IVAL == 0:
                now = datetime.datetime.now()
                print("Waiting... {:3d} | {}".format(i, now.strftime("%H:%M:%S")))
                # TODO: rmm add uptime to this msg. Wed 17 Feb 2021 11:22:47 CET

            if imax is not None and i >= imax:
                break

    #}}}

if __name__ == "__main__": #noqa
    #{{{ cmd-line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--addr', required=True,
                        help="address of the BLE peripheral with NRF LEDBUTTON service")
    #parser.add_argument('-v', '--verb', action='store_true')
    parser.add_argument('-v', '--verb', action='count', default=0)
    parser.add_argument('-ci', '--conv_incoming', action='store_true',
                        help="switch to show converted incoming data or raw bytes")
    parser.add_argument('-i', '--imax', type=int, default=None,
                        help="maximum iterations to listen for, leave as none to wait forever (/until ctrl-c)")
    parser.add_argument('-r', '--max_retries', type=int, default=3)
    parser.add_argument('-f', '--log_format', type=int, default=2, choices=[1,2],
                        help="how to store data: 1) raw binary strings or 2) interpreted numbers")
    parser.add_argument('-l', '--exptlbl', type=str, default="",
                        help="label to give to all log files.")
    parser.add_argument('-o', '--logdir', type=str, default=None,
                        help="path to create and save logs to.  If None, no data written.")
    args = parser.parse_args()

    #addr_type = btle.ADDR_TYPE_PUBLIC
    addr_type = btle.ADDR_TYPE_RANDOM
    #}}}

    syslog = None
    if args.logdir is not None:
        syslog = "{}/{}.syslog".format(args.logdir, args.exptlbl)
        # needs mkdir here!
        mkdir_p(args.logdir)
    else:
        print("[W]======= NO LOGFILE GIVEN -> NO SYSLOG RECORDS ========\n"*5)

    #{{{ reconnector loop
    retry_cnt = 0
    conn = None
    while True:
        try:
            s1 = "Connecting to: {}, address type: {}. {}th time".format(
                args.addr, addr_type, retry_cnt)
            dump_log_line(syslog, s1)
            conn = btle.Peripheral(args.addr, addr_type)
            # try setting the time?
            ret = settime(conn)
            if ret is not None:
                s1 = "[I] time set ok to {}".format(ret)
                dump_log_line(syslog, s1)

            mainloop(conn, args.addr, args.exptlbl, args.logdir, verb=args.verb,
                     imax=args.imax, sleep_period=0.5, conv_inc=args.conv_incoming,
                     logfmt=args.log_format)
        except KeyboardInterrupt as e:
            s1 = "[I] ctrl c pressed. bye."
            dump_log_line(syslog, s1)

            break
        except btle.BTLEDisconnectError as e:
            s1 = "[W] peer disconnected-(re)try {}".format(retry_cnt)
            dump_log_line(syslog, s1)
            conn.disconnect()
            s1 = "[W] sleeping 15s before reconnect attempt {}".format(retry_cnt)
            dump_log_line(syslog, s1)
            time.sleep(15.0)

            retry_cnt += 1
            if retry_cnt > args.max_retries:
                s1 = "[W] reached {} retries (>{}). stopping".format(retry_cnt, args.max_retries)
                dump_log_line(syslog, s1)
                break
    #}}}

    if conn is not None:
        conn.disconnect()
        s1 = "[I] disconnected from peer {}.".format(args.addr)
    else:
        s1 = "[W] did not make connection to peer {}".format(args.addr)
    dump_log_line(syslog, s1)




