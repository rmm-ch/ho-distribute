from bluepy.btle import Scanner, DefaultDelegate
import libscn

# note: this must be run as root (or at least with root priviledges setup for
# bluepy-helper. One solution to give permissions:
# https://github.com/IanHarvey/bluepy/issues/313
#   sudo setcap 'cap_net_raw,cap_net_admin+eip' bluepy-helper
#
# or possibly
#   sudo setcap cap_net_raw+e  <PATH>/bluepy-helper
#   sudo setcap cap_net_admin+eip  <PATH>/bluepy-helper
#
# after looking up the explicit location of the helper library.



scanner = libscn.Scanner().withDelegate(libscn.ScanDelegate())
devices = scanner.scan(5.0)

#x = libscn.disp_dev_info(devices)
print("[I] scanning for MOBOTS tags")
y = libscn.get_mobots_tags(devices, verb=True)

z = libscn.get_mobots_addrs(devices)

print("[I] found {} MOBOTS tags".format(len(z)))
print("\t" + str(z))

