import bluepy.btle as btle
import struct
import time
import datetime as dt

#{{{ UUIDs
HO_SNSR_SVC          = "00005001-bee5-bee5-0001-bee5bee5bee5"
HO_SNSR_CHR_DATA_RAW = "00006001-bee5-bee5-0001-bee5bee5bee5"
HO_SNSR_CHR_DATA_FMT = "00006101-bee5-bee5-0001-bee5bee5bee5"
HO_SNSR_CHR_CFG_HDC  = "00007011-bee5-bee5-0001-bee5bee5bee5"
#HO_SNSR_CHR_CFG_SCD  = "00007021-bee5-bee5-0001-bee5bee5bee5"

HO_TIME_SVC          = "00001001-bee5-bee5-0002-bee5bee5bee5"
HO_TIME_SET_CHAR     = "00003001-bee5-bee5-0002-bee5bee5bee5"
#}}}

# {{{ HO cfg interface definitions
''' definitions etc for interface
      // MSb:LSb
      // 76543210
      // ||---------- cls 2b
      //   |||------- grp 3b
      //      |||---- subcmd 3b
'''

def _ho_construct_command(thecls, grp, cmd):
    return ((thecls << 6) | (cmd <<3) | (0x07 & cmd))


HO_CFG_CLS0  = 0x00
HO_CFG_CLS8  = 0x01
HO_CFG_CLS16 = 0x02

HO_CFGGRP_HDC    = 0x000
HO_CFGGRP_SCD30  = 0x001
HO_CFGGRP_I2CDOM = 0x002
HO_CFGGRP_TIMERS = 0x003


HO_CFGCMD_HDC_SETPERIOD  =  0x00 #0b00
HO_CFGCMD_HDC_SETRPT     =  0x01 #0b01
HO_CFGCMD_HDC_SETHEATER  =  0x02 #0b10

HO_CFGCMD_SCD_STOPSAMP   = 0x02
# 1 trigger 2 stop 3 set meas ival 4 get ready 5 read data 6 ASC, FRC
# 7 temp offset 8 altitude 9 firmare 10=A soft reset.

HO_CFGCMD_TIM_HDCSAMP = 0x00
HO_CFGCMD_TIM_HDCEMIT = 0x01
HO_CFGCMD_TIM_SCDSAMP = 0x02
HO_CFGCMD_TIM_SCDEMIT = 0x03
HO_CFGCMD_TIM_SCDFSM  = 0x04
HO_CFGCMD_TIM_BATSAMP = 0x05
HO_CFGCMD_TIM_BATEMIT = 0x06


HO_CFG_HDC_SET_PERIOD = ((HO_CFG_CLS8) << 6) | ((HO_CFGGRP_HDC) << 3) | (0x03 & HO_CFGCMD_HDC_SETPERIOD)
HO_CFG_HDC_SET_REPEAT = ((HO_CFG_CLS8) << 6) | ((HO_CFGGRP_HDC) << 3) | (0x03 & HO_CFGCMD_HDC_SETRPT)
HO_CFG_HDC_SET_HEATER = ((HO_CFG_CLS8) << 6) | ((HO_CFGGRP_HDC) << 3) | (0x03 & HO_CFGCMD_HDC_SETHEATER)

HO_CFG_TIMERHDC_INTERVAL = _ho_construct_command(HO_CFG_CLS16, HO_CFGGRP_TIMERS, HO_CFGCMD_TIM_HDCSAMP)
HO_CFG_TIMERHDC_BULKEMIT = _ho_construct_command(HO_CFG_CLS16, HO_CFGGRP_TIMERS, HO_CFGCMD_TIM_HDCEMIT)
HO_CFG_TIMERSCD_INTERVAL = _ho_construct_command(HO_CFG_CLS16, HO_CFGGRP_TIMERS, HO_CFGCMD_TIM_SCDSAMP)
HO_CFG_TIMERSCD_BULKEMIT = _ho_construct_command(HO_CFG_CLS16, HO_CFGGRP_TIMERS, HO_CFGCMD_TIM_SCDEMIT)
HO_CFG_TIMERSCD_FSM      = _ho_construct_command(HO_CFG_CLS16, HO_CFGGRP_TIMERS, HO_CFGCMD_TIM_SCDFSM)
HO_CFG_TIMERBAT_INTERVAL = _ho_construct_command(HO_CFG_CLS16, HO_CFGGRP_TIMERS, HO_CFGCMD_TIM_BATSAMP)
HO_CFG_TIMERBAT_BULKEMIT = _ho_construct_command(HO_CFG_CLS16, HO_CFGGRP_TIMERS, HO_CFGCMD_TIM_BATEMIT)

HO_CFG_SCD_STOPSAMP = _ho_construct_command(HO_CFG_CLS0, HO_CFGGRP_SCD30, HO_CFGCMD_SCD_STOPSAMP)


AMM_DISABLED = 0x0 #
AMM_120_SEC  = 0x1 # //001
AMM_60_SEC   = 0x2 #
AMM_10_SEC   = 0x3 #
AMM_5_SEC    = 0x4 # //100
AMM_1_SEC    = 0x5 # //101
AMM_2HZ      = 0x6 #
AMM_5HZ      = 0x7 #
AMM_1HZ      = 0x5 # // alias for AMM_1_SEC, 101

_HO_I2CDOM_ON     = 0x3
_HO_I2CDOM_OFF    = 0x0
_HO_I2CDOM_TOGGLE = 0x1

HO_CFG_I2CDOM_ON     =   ((HO_CFG_CLS0) << 6) | ((HO_CFGGRP_I2CDOM) << 3) | (0x07 & _HO_I2CDOM_ON)
HO_CFG_I2CDOM_OFF    =   ((HO_CFG_CLS0) << 6) | ((HO_CFGGRP_I2CDOM) << 3) | (0x07 & _HO_I2CDOM_OFF)
HO_CFG_I2CDOM_TOGGLE =   ((HO_CFG_CLS0) << 6) | ((HO_CFGGRP_I2CDOM) << 3) | (0x07 & _HO_I2CDOM_TOGGLE)


# }}}
# {{{ typical usage
''' typical usage
1. establish connection
2. lookup service, and characteristic
3. transmit specific packet on that char
4. done, disconnect.

    s1 = "Connecting to: {}, address type: {}. {}th time".format(
        args.addr, addr_type, retry_cnt)
    dump_log_line(syslog, s1)
    conn = btle.Peripheral(args.addr, addr_type)
    # try setting the time?
    ret = settime(conn)
    if ret is not None:
        s1 = "[I] time set ok to {}".format(ret)
        dump_log_line(syslog, s1)
'''
# }}}

#{{{ connection lookup
def lookup_crs(svc, TGT_UUID, lbl=""):
    # we can look at the characteristics offered with this service
    _all_crs = svc.getCharacteristics()
    tgt_crs = None
    for _c in _all_crs:
        print("{} {} {}".format(_c.propertiesToString(), _c.uuid.getCommonName(),  _c.valHandle))
        if _c.uuid.getCommonName() == TGT_UUID:
            print("[I] we found the '{}' characteristic.".format(lbl))
            tgt_crs = _c
    return tgt_crs
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
#{{{ comparetime
def comparetime(conn):
    svc = conn.getServiceByUUID(HO_TIME_SVC)
    settime_crs = lookup_crs(svc, HO_TIME_SET_CHAR, "time setter")
    if settime_crs is None:
        print("[W] failed to find time setter/getter char (uuid:{}). Time not set.".format(
            HO_TIME_SET_CHAR))
        return None

    time.sleep(0.1)
    now  = int(time.time())
    msg = struct.pack("<I", now);
    print("[I] to set, would transmit '{}' ({}by) to val {}".format(msg, len(msg), settime_crs.valHandle))
    #conn.writeCharacteristic(settime_crs.valHandle, msg);
    # try reading settime_crs
    data = settime_crs.read()
    if data:
        t_nrf = int(struct.unpack("<I", data)[0])
        diff = now - t_nrf
        #readCharacteristic
        t_str = dt.datetime.fromtimestamp(t_nrf).strftime('%Y-%m-%d %H:%M:%S')
        t_loc = dt.datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')
        print("[I] read back {} by:       '{}' -> {}".format( len(data), data, t_nrf))
        print("[I] nrf time = {}, {}s diff.".format(t_str, diff))
        return t_nrf
    else:
        print("[W] didn't receive any data!");
        return None


#}}}



#{{{ snsr_cfg
def snsr_cfg8_hdc(conn, arg8):
    cmd = HO_CFG_HDC_SET_PERIOD
    return snsr_cfg8(conn, cmd, arg8)

def snsr_cfg_i2cdomain(conn, opt):
    '''
    opt should be in [_HO_I2CDOM_ON, _HO_I2CDOM_OFF, _HO_I2CDOM_TOGGLE]

    //arg8 should be in [HO_CFG_I2CDOM_ON, HO_CFG_I2CDOM_OFF, HO_CFG_I2CDOM_TOGGLE]
    '''
    if opt not in [_HO_I2CDOM_ON, _HO_I2CDOM_OFF, _HO_I2CDOM_TOGGLE]:
        print("[W] arg not recognised ({}), no action attempted.".format(opt))
        return None
    cmd = HO_CFG_I2CDOM_ON
    if opt == _HO_I2CDOM_OFF:
        cmd = HO_CFG_I2CDOM_OFF
    elif opt == _HO_I2CDOM_TOGGLE:
        cmd = HO_CFG_I2CDOM_TOGGLE

    return snsr_cfg0(conn, cmd)

def snsr_cfg0(conn, cmd):
    svc = conn.getServiceByUUID(HO_SNSR_SVC)
    cfg_crs = lookup_crs(svc, HO_SNSR_CHR_CFG_HDC, "cfg - hdc")
    if cfg_crs is not None:
        time.sleep(0.1)
        msg = struct.pack("<B", cmd);
        hexmsg = "".join(["{:02x}".format(b) for b in bytearray(msg)])
        print("[I] will transmit '{}'[{}] ({}by) to val {}".format(msg, hexmsg, len(msg), cfg_crs.valHandle))
        conn.writeCharacteristic(cfg_crs.valHandle, msg);
        return hexmsg

    else:
        print("[W] failed to find cfg char (uuid:{}). cmd not sent.".format(
            HO_SNSR_CHR_CFG_HDC))
        return None


def snsr_cfg8(conn, cmd, arg8):
    svc = conn.getServiceByUUID(HO_SNSR_SVC)
    cfg_crs = lookup_crs(svc, HO_SNSR_CHR_CFG_HDC, "cfg - hdc")
    if cfg_crs is not None:
        time.sleep(0.1)
        #HO_CFG_HDC_SET_PERIOD = ((HO_CFG_CLS8) << 6) | ((HO_CFGGRP_HDC) << 3) | (0x03 & HO_CFGCMD_HDC_SETPERIOD)
        #HO_CFG_HDC_SET_REPEAT = ((HO_CFG_CLS8) << 6) | ((HO_CFGGRP_HDC) << 3) | (0x03 & HO_CFGCMD_HDC_SETRPT)
        #HO_CFG_HDC_SET_HEATER = ((HO_CFG_CLS8) << 6) | ((HO_CFGGRP_HDC) << 3) | (0x03 & HO_CFGCMD_HDC_SETHEATER)
        #cmd = HO_CFG_HDC_SET_PERIOD
        #arg8 = AMM_10_SEC
        #now  = int(time.time())
        msg = struct.pack("<BB", cmd, arg8);
        hexmsg = "".join(["{:02x}".format(b) for b in bytearray(msg)])
        print("[I] will transmit '{}'[{}] ({}by) to val {}".format(msg, hexmsg, len(msg), cfg_crs.valHandle))
        conn.writeCharacteristic(cfg_crs.valHandle, msg);
        return hexmsg

    else:
        print("[W] failed to find time setter char (uuid:{}). Time not set.".format(
        HO_TIME_SET_CHAR))
        return None

def snsr_cfg16(conn, cmd, arg16):
    svc = conn.getServiceByUUID(HO_SNSR_SVC)
    cfg_crs = lookup_crs(svc, HO_SNSR_CHR_CFG_HDC, "cfg - hdc")
    if cfg_crs is not None:
        time.sleep(0.1)
        #now  = int(time.time())
        msg = struct.pack("<BH", cmd, arg16);
        hexmsg = "".join(["{:02x}".format(b) for b in bytearray(msg)])
        print("[I] will transmit '{}'[{}] ({}by) to val {}".format(msg, hexmsg, len(msg), cfg_crs.valHandle))
        conn.writeCharacteristic(cfg_crs.valHandle, msg);
        return hexmsg

    else:
        print("[W] failed to find time setter char (uuid:{}). Time not set.".format(
        HO_TIME_SET_CHAR))
        return None
#}}}
#{{{ dump_log_line
def dump_log_line(logfile, line, prefix="#", echo=True):
    if echo:
        print(line)

    pre2 = "{:.3f}|".format(time.time())
    if logfile is not None:
        with(open(logfile, "a")) as lf:
            lf.write("{}{}{}\n".format(prefix, pre2, line))
#}}}
