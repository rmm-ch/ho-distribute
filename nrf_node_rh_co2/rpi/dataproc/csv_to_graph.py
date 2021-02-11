#!/usr/bin/env python3
'''
plot data from a triplet of log files - assumes already converted to CSV
example usage:
    $ ipython
    > %run csv_to_graph.py --logdir <path to where your csv files were saved>



'''

import argparse
import os.path, fnmatch
import pandas as pd
import matplotlib.pyplot as plt
#import numpy as np

def lookup_logs(pth, prefix=None):
    ''' assumes one set of logs in any given directory.'''
    fn_scd, fn_hdc, fn_bat = None, None, None
    if prefix is None:
        prefix = ""
    for fn in os.listdir(pth):
        if fnmatch.fnmatch(fn, "{}*datscd.csv".format(prefix)):
            fn_scd = os.path.join(pth, fn)
        if fnmatch.fnmatch(fn, "{}*dathdc.csv".format(prefix)):
            fn_hdc = os.path.join(pth, fn)
        if fnmatch.fnmatch(fn, "{}*batlvl.csv".format(prefix)):
            fn_bat = os.path.join(pth, fn)

    return (fn_scd, fn_hdc, fn_bat)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verb', action='store_true')
    parser.add_argument('-d', '--logdir', type=str, required=True)

    args = parser.parse_args()

    # lazy / fragile lookup of log filenames
    fn_scd, fn_hdc, fn_bat = lookup_logs(args.logdir)

    # load the scd and hdc2010 data
    df_scd = pd.read_csv(fn_scd)
    df_hdc = pd.read_csv(fn_hdc)
    # turn the unix timestamps into interpretable datetime objects
    df_scd["timestamp"] = pd.to_datetime(df_scd.timestamp, unit='s')
    df_hdc["timestamp"] = pd.to_datetime(df_hdc.timestamp, unit='s')

    # do some simple plots
    axs_s = df_scd.plot(x="timestamp", y=["T", "RH", "CO2"], color="C0", subplots=True)
    #axs_h = df_hdc.plot(x="timestamp", y=["T", "RH", ], subplots=True)

    df_hdc.plot(x="timestamp", y="T", ax=axs_s[0], c='C3', label="T hdc2010")
    df_hdc.plot(x="timestamp", y="RH", ax=axs_s[1], c='C3', label="RH hdc2010")
    units = ["Temperature ($^o$C)", "Rel. Humidity (%)", "CO$_2$ (ppm)"]
    for i, a in enumerate(axs_s):
        a.set_ylabel(units[i])
        a.grid(True)
    plt.tight_layout()

