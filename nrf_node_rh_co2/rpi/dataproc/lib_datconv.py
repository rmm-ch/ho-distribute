#!/usr/bin/env python3

import struct
import pandas as pd
import numpy as np
import datetime as dt

#{{{ human-readable formatting
def fmt_time(time_s, fmt='%H:%M:%S'):
    return dt.datetime.fromtimestamp(time_s).strftime('%H:%M:%S')
#}}}

#{{{ convert binary to natural formats
def bytes_to_u32(b, bigendian=True):
    if bigendian:
        u32 = (b[0] | b[1] << 8 | b[2] << 16 | b[3] << 24)
    else:
        u32 = (b[3] | b[2] << 8 | b[1] << 16 | b[0] << 24)

    return u32

def bytes_to_u16(b, bigendian=True):
    if bigendian:
        u16 = (b[0] | b[1] << 8 )
    else:
        u16 = (b[1] | b[0] << 8)

    return u16
#}}}

#{{{ handling of battery data
def dump_batlvl_to_csv(Dbat, fname, header=True):
    cols = ["timestamp", "Vbat", "Vdd"]

    df = pd.DataFrame(Dbat, columns=cols)
    if fname is not None:
        df.to_csv(fname, header=header, index=False)
    else:
        print("[W] df not written to file - no path given")

    return df

def load_batlvl_file(logfile, verb=False):# {{{
    # try reading from logfile
    with open(logfile, "r") as lf:
        lines = lf.readlines()

    _D = []
    for li in lines:
        l = li.strip()
        if set(l) != set('0'):
            # zero strings come currently due to a modulo issue. ignore.
            # still getting these?
            _D.append(conv_bat_from_bytes(l))
            if verb:
                s = str_bat_from_bytes(l)
                print("{}\t{}".format(l, s))

    D = np.array(_D)
    return D
# }}}

def conv_bat_from_bytes(bytestr):
    B = bytes.fromhex(bytestr)
    # 0:4 -> timestamp
    # 4:6 -> i_batmon
    # 6:8 -> i_vdd
    b_ts   = B[0:4]
    b_bat  = B[4:6]
    b_vdd  = B[6:8]

    time_s = bytes_to_u32(b_ts)
    i_bat = bytes_to_u16(b_bat)
    i_vdd = bytes_to_u16(b_vdd)

    #uint32_t v_meas = i_bat_mon * 3.515625f;  // 1000x larger, for simple "float" print
    #uint32_t v_bat = v_meas * 65536 /46711;   // voltage divider
    #uint32_t v_vdd = i_vdd * 3.515625f;       // 1000x larger


    v_bat = (i_bat * 3.515625) * (65536.0 / 46711.0 ) * (1.0/1000.0)
    v_vdd = i_vdd * 3.515625 / 1000.0



    return (time_s, v_bat, v_vdd)


def str_bat_from_bytes(bytestr):
    (time_s, v_bat, v_vdd) = conv_bat_from_bytes(bytestr)
    s = "{}  Vbat {:.3f} Vdd {:.3f}".format(
        fmt_time(time_s), v_bat, v_vdd)
    return s
#}}}

# {{{ handling of HDC2010 data

# {{{ converters
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

def conv_hdc_t0_from_bytes(bytestr):
    B = bytes.fromhex(bytestr)
    u32_time_s_x10 = B[8] | B[9] << 8 | B[10] << 16 | B[11] << 24;
    return (u32_time_s_x10 / 10.0)

def conv_hdc_utc_from_bytes(bytestr):
    B = bytes.fromhex(bytestr)
    u32_time_s = B[8] | B[9] << 8 | B[10] << 16 | B[11] << 24;
    return (u32_time_s)

def conv_hdc_from_bytes(bytestr, ty4=True):
    f_temp     = conv_hdc_T_from_bytes(bytestr)
    f_hum_pct  = conv_hdc_RH_from_bytes(bytestr)
    f_timestep = conv_hdc_ts_from_bytes(bytestr)
    if len(bytestr)>= 12:
        #f_time_s = conv_hdc_t0_from_bytes(bytestr)
        utime_s = conv_hdc_utc_from_bytes(bytestr)
        if ty4:
            return (f_temp, f_hum_pct, f_timestep, utime_s)

    return (f_temp, f_hum_pct, f_timestep)


def disp_hdc_from_bytes(bytestr, ty4=True, utimes=False):
    #(f_temp, f_hum_pct, f_timestep) = conv_hdc_from_bytes(bytestr, ty4=ty4)
    (f_temp, f_hum_pct, f_timestep, f_time_s) = conv_hdc_from_bytes(bytestr, ty4=ty4)
    if utimes:
        print("{:10}s {:6}:{:+5.3f}oC {:.2f}%RH".format(f_time_s, f_timestep, f_temp, f_hum_pct))
    else:
        print("{:6.2f}s {:6}:{:+5.3f}oC {:.2f}%RH".format(f_time_s, f_timestep, f_temp, f_hum_pct))
    #print("{:4}:{:+5.3f}oC {:.2f}%RH".format(f_timestep, f_temp, f_hum_pct))



# }}}
def load_hdc_file(logfile, utimes, verb=False, sry=True ):
    # try reading from logfile
    with open(logfile, "r") as lf:
        lines = lf.readlines()

    _D = []
    for li in lines:
        l = li.strip()
        #(f_temp, f_hum_pct, f_timestep) = conv_hdc_from_bytes(bytestr)
        if set(l) != set('0'):
            # zero strings come currently due to a modulo issue. ignore.
            # this is also really stupidly ordered - instead, do timestep first
            (f_temp, f_hum_pct, f_timestep, utime_s) = conv_hdc_from_bytes(l)
            _D.append((utime_s, f_temp, f_hum_pct, f_timestep))
            #_D.append(conv_hdc_from_bytes(l))
        if verb:
            print(l, end='\t')
            disp_hdc_from_bytes(l, utimes=utimes)

    if not verb and sry:# just show first and last
        for i in [0, len(lines)-2, len(lines)-1]:
            l=lines[i].strip()
            print(l, end='\t')
            disp_hdc_from_bytes(l, utimes=utimes)

    D = np.array(_D)
    if sry or verb:
        print("[I] HDC data - read {} lines. Range :{}--{} ({}s)".format(
            D.shape[0], D[0,3], D[-1,3], D[-1,3]-D[0,3]))
    return D


def dump_hdcdat_to_csv(Dhdc, fname, header=True):
    cols = ["timestamp", "T", "RH", "seq"]

    df = pd.DataFrame(Dhdc, columns=cols)
    if fname is not None:
        df.to_csv(fname, header=header, index=False)
    else:
        print("[W] df not written to file - no path given")

    return df

# }}}

#{{{ handling SCD30 data
def str_scd_from_bytes(bytestr):
    (time_s, seq, co2, temp, RH) = conv_scd_from_bytes(bytestr)
    s = "{:10} {:5}:{:+5.3f}oC {:.2f}%RH {:6.2f}ppm".format(time_s, seq, temp, RH, co2)
    return s

def conv_scd_from_bytes(bytestr):
    B = bytes.fromhex(bytestr)
    # 0:4 -> timestamp
    # 4:8 -> sequence
    # 8:12   CO2, in float format
    # 12:16  temp in float format
    # 16:20  RHum in float format
    b_ts   = B[0:4]
    b_seq  = B[4:8]
    b_co2  = B[8:12]
    b_temp = B[12:16]
    b_rh   = B[16:20]

    seq = bytes_to_u32(b_seq)
    time_s = bytes_to_u32(b_ts)

    # not sure why endian change here? did I transmit in reverse?
    #memcpy(&buffer[8], (uint32_t*)&p_tag_data->p_scd30_data->raw_CO2, 4);
    # anyway, the data is received this way around.
    temp = struct.unpack("<f", b_temp)[0]
    co2  = struct.unpack("<f", b_co2)[0]
    RH   = struct.unpack("<f", b_rh)[0]


    return (time_s, seq, co2, temp, RH)


def load_scd_file(logfile, utimes, verb=False, sry=True):
    # try reading from logfile
    with open(logfile, "r") as lf:
        lines = lf.readlines()

    _D = []
    for li in lines:
        l = li.strip()
        #(f_temp, f_hum_pct, f_timestep) = conv_hdc_from_bytes(bytestr)
        if set(l) != set('0'):
            # zero strings come currently due to a modulo issue. ignore.
            _D.append(conv_scd_from_bytes(l))
        if verb:
            s = str_scd_from_bytes(l)
            print("{}\t{}".format(l, s))

    if not verb and sry:# just show first and last
        for i in [0, len(lines)-2, len(lines)-1]:
            l=lines[i].strip()
            s = str_scd_from_bytes(l)
            print("{}\t{}".format(l, s))

    D = np.array(_D)
    if sry or verb:
        print("[I] SCD data - read {} lines. Range :{}--{} ({}s)".format(
            D.shape[0], D[0,3], D[-1,3], D[-1,3]-D[0,3]))
    return D

def dump_scddat_to_csv(Dscd, fname, header=True):
    cols = ["timestamp", "seq", "CO2", "T", "RH"]

    df = pd.DataFrame(Dscd, columns=cols)
    if fname is not None:
        df.to_csv(fname, header=header, index=False)
    else:
        print("[W] df not written to file - no path given")

    return df
#}}}
