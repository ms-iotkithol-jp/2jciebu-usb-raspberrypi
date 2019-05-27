!/bin/bash
sudo modprobe ftdi_sio 
sudo chmod 777 /sys/bus/usb-serial/drivers/ftdi_sio/new_id 
sudo echo 0590 00d4 > /sys/bus/usb-serial/drivers/ftdi_sio/new_id

