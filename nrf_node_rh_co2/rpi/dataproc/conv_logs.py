#!/usr/bin/env python3
'''
Main goal here is to convert logfiles from MOBOTS nRF52 wireless sensor,
containing binary-encoded values, into interpretable values and save into
csv files.
'''
import argparse
import numpy as np
import os.path

import lib_datconv as libdata


#{{{ class LogHandles
class LogHandles:
    '''
    a container to generate the expected filenames for MOBOTS nRF tag logs.

    input an argparse object, with the properties
      args.logdir
      args.logpath

    and this will generate the appropriate filenames for:
        self.logfile  (if not None, the others are derived from it)
        self.logf_scd
        self.logf_bat

    the filenames are somewhat fragile, and really need updating.

    '''
    def __init__(self, args, verb=False):
        self.args = args
        self.logdir = args.logdir
        self.inc_scd = False
        self.inc_hdc = False
        self.inc_bat = False
        if verb:
            print("[D] -- args are: ", args)
            print("[D] logdir  : {}".format(args.logdir))
            print("[D] logfile : {}".format(args.logfile))


        if self.args.logfile is not None:
            self.logfile = args.logfile

            self.logf_scd = "{}-{}{}".format(
                args.logfile[:-4], "datscd", args.logfile[-4:])
            self.logf_bat = "{}-{}{}".format(
                args.logfile[:-4], "batlvl", args.logfile[-4:])
            self.logf_bat = "{}-{}{}".format(
                args.logfile[:-4], "dathdc", args.logfile[-4:])

        elif self.args.logdir is not None:
            # now we need to do a lookup or somehow know the dates/labels.
            #pth/<date>_<lbl>.<ext>
            #200826_test.dathdc
            #args.logf_hdc
            self.logfile  = "{}.{}".format(self.args.logdir, "dathdc")
            self.logf_scd = "{}.{}".format(self.args.logdir, "datscd")
            self.logf_bat = "{}.{}".format(self.args.logdir, "batlvl")

        else:
            raise RuntimeError("[F] no log info given! No graphs possible. bye.")

        # now check which files exist


        self.inc_scd = os.path.exists(self.logf_scd)
        self.inc_hdc = os.path.exists(self.logfile)
        self.inc_bat = os.path.exists(self.logf_bat)
        print("[I] looking for scd log {}. found? {}".format(self.logf_scd, self.inc_scd))
        print("[I] looking for hdc log {}. found? {}".format(self.logfile,  self.inc_hdc))
        print("[I] looking for bat log {}. found? {}".format(self.logf_bat, self.inc_bat))

#}}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verb', action='store_true')
    parser.add_argument('-nh', '--no_header', action='store_true')
    parser.add_argument('-e', '--emit', action="store_true",
                        help="emit .csv files if set.")
    parser.add_argument('-l', '--logfile', type=str, default=None) #required=True)
    # best not to specfiy logfile here -- mess with formatting of filenames. # (keep=None)
    parser.add_argument('-d', '--logdir', type=str, default=None)

    args = parser.parse_args()

    LH1 = LogHandles(args, verb=args.verb)
    Dscd, Dbat, Dhdc = None, None, None

    if LH1.inc_scd:
        Dscd = libdata.load_scd_file(LH1.logf_scd, args.verb)
        fn = None
        if args.emit:
            fn = "{}.csv".format(LH1.logf_scd)
        df_scd = libdata.dump_scddat_to_csv(Dscd, fn, not(args.no_header))


    if LH1.inc_bat:
        Dbat = libdata.load_batlvl_file(LH1.logf_bat, args.verb)
        fn = None
        if args.emit:
            fn = "{}.csv".format(LH1.logf_bat)
        df_bat = libdata.dump_batlvl_to_csv(Dbat, fn, not(args.no_header))

    #BPC = libdata.BatPctConverter()
    if LH1.inc_hdc:
        Dhdc = libdata.load_hdc_file(LH1.logfile, True, args.verb)
        fn = None
        if args.emit:
            fn = "{}.csv".format(LH1.logfile)
        df_hdc = libdata.dump_hdcdat_to_csv(Dhdc, fn, not(args.no_header))



