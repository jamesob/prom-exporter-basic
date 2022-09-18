
# prom-exporter-basic

A very basic prometheus exporter that doesn't involve downloading some opaque go binary
and running it with full access to your /proc filesystem. Nice right?

The only dependencies are Python 3.


## Installation

1. Get `main.py` somehow.
1. Run it.

## Output sample

```
disk_bytes_used{host=fido,mount=/dev,device=udev} 0
disk_bytes_avail{host=fido,mount=/dev,device=udev} 65889984
disk_used_percent{host=fido,mount=/dev,device=udev} 0
disk_bytes_used{host=fido,mount=/,device=/dev/mapper/fido--vg-root} 985187808
disk_bytes_avail{host=fido,mount=/,device=/dev/mapper/fido--vg-root} 836935932
disk_used_percent{host=fido,mount=/,device=/dev/mapper/fido--vg-root} 55
disk_bytes_used{host=fido,mount=/boot,device=/dev/nvme0n1p2} 51181
disk_bytes_avail{host=fido,mount=/boot,device=/dev/nvme0n1p2} 405476
disk_used_percent{host=fido,mount=/boot,device=/dev/nvme0n1p2} 12
disk_bytes_used{host=fido,mount=/boot/efi,device=/dev/nvme0n1p1} 3488
disk_bytes_avail{host=fido,mount=/boot/efi,device=/dev/nvme0n1p1} 519760
disk_used_percent{host=fido,mount=/boot/efi,device=/dev/nvme0n1p1} 1
cpu_load_1min{host=fido} 2.24
cpu_load_5min{host=fido} 2.06
cpu_load_15min{host=fido} 2.09
net_KB_in{host=fido,device=enp6s0} 17.11
net_KB_out{host=fido,device=enp6s0} 11.59
net_KB_in{host=fido,device=somenet} 0.00
net_KB_out{host=fido,device=somenet} 0.09
net_KB_in{host=fido,device=wg0} 0.00
net_KB_out{host=fido,device=wg0} 0.00
```
