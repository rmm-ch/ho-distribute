from bluepy.btle import Scanner, DefaultDelegate

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print("Discovered device", dev.addr)
        elif isNewData:
            print("Received new data from", dev.addr)

def disp_dev_info(devices, verb=False):
    subset = []
    for dev in devices:
        t3 = dev.getValueText(3)
        if t3 is not None:
            subset.append(dev)
            if verb:
                print("Device %s (%s), RSSI=%d dB. t3: %s" % (dev.addr, dev.addrType, dev.rssi, str(t3)))

            if verb:
                for (adtype, desc, value) in dev.getScanData():
                #if adtype == 3:
                    print( "  %s = %s" % (desc, value))
    return subset


def get_mobots_tags(devices, verb=False):
    subset = []
    for dev in devices:
        t3 = dev.getValueText(3) # 16b Services
        if t3 is None:
            continue
        #0000180a-0000-1000-8000-00805f9b34fb
        if t3.startswith("0000180a"):
            subset.append(dev)
            if verb:
                print("   Device %s (%s), RSSI=%d dB. t3: %s" % (dev.addr, dev.addrType, dev.rssi, str(t3)))
                for (adtype, desc, value) in dev.getScanData():
                    print( "    %s = %s" % (desc, value))

    return subset

def get_mobots_addrs(devices):
    '''
    given a list of device objects (returned by bluepy.btle.Scanner.scan())
    filter for mobots tags and extract just the mac addresses
    '''
    addrs = []
    for dev in devices:
        t3 = dev.getValueText(3) # 16b Services
        if t3 is None:
            continue
        if t3.startswith("0000180a"):
            # filter on the services info char
            addrs.append(str(dev.addr).upper())

    return addrs




