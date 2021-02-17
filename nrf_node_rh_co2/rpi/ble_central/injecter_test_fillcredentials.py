import datetime as dt
from influxdb import InfluxDBClient
import argparse

'''
inject data point by point from a log file
no error checking!
'''

def read_creds():
    with open('/home/pi/.influx_creds', 'r') as f:
        username = next(f).strip().split('username=')[-1]
        password = next(f).strip().split('password=')[-1]
        database = next(f).strip().split('database=')[-1]
    return username, password, database


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verb', action='store_true')
    parser.add_argument('-i', '--infile', type=str, default=None)
    parser.add_argument('-a', '--addr', type=str,required=True)
    parser.add_argument('-n', '--num', type=int, default=4)
    args = parser.parse_args()

    ifuser, ifpass, ifdb = read_creds()
    ifhost = "localhost";
    ifport = 8086;

    ifclient = InfluxDBClient(ifhost, ifport, ifuser, ifpass, ifdb)

    print(ifclient.ping())
    print(ifclient.get_list_measurements())
    print(ifclient.get_list_users())


    with open(args.infile) as f:
        for i, line in enumerate(f.readlines()):
            if not line.startswith("timestamp"):
                t, seq, co2, temp, RH = [float(x) for x in line.split(',')]
                print(i,t, seq, co2, temp, RH)
                point = {
                    "measurement": "scd30",
                    "tags": { "nrf_addr": args.addr, },
                    "time": dt.datetime.fromtimestamp(t).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    "fields": { "co2": co2, "temp": temp, "rel_hum": RH, },
                }
                rv = ifclient.write_points([point])




