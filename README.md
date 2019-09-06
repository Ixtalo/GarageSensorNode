

Garage Sensor Node via Power Line Modem
=======================================

This project realizes sending UART serial protocol data via power line, the sender being an Arduino board, the receiver is a Raspberry Pi and a Python program which published to MQTT.  

## Challenge
The challenge has been to send data (e.g., temperature sensor readings) from the outside garage to the server inside the main house. The gerage is located away from the house and multiple concrete walls are blocking the line of sight, making radio communication almost impossible.  

But, there is one single phased power line between the house and the garage. Only the power line, no empty conduit.  

## Solution
The solution is to use the power line as a carrier. A power line modem is used to send sensor readings periodically over the power line.  

The involved components:  
* Arduino Pro mini as sender
  * `garagenode_sender/garagenode_sender.ino`
* Raspberry Pi 2a as receiver
  * `garagenode_receiver/garagenode_receiver_mqtt.py`
* 2 power line modems, KQ-330F (KQ-330), UART

Schematics:  
`SENSORS <---> Arduino <---> Modem <-- Power line --> Modem <---> Raspberry Pi`



## Power Line Communication
![Power Line Modem KQ-130F](doc/kq-130f_kq330.jpg)

* KQ-130F
	* https://forum.fhem.de/index.php?topic=51046.0
* Mamba - Narrow Band Powerline Communication Shield for Arduino
	* http://cutedigi.com/mamba-narrow-band-powerline-communication-shield-for-arduino/
* X10 Protokoll (129 kHz)
* HomePlug Green PHY
	* https://www.codico.com/de/Produkte/HomePlug-Green-Phy.htm
	* https://smartcharging.in-tech.com/product/plc-stamp-1/


## Arduino & Robust Serial Communication
* https://stackoverflow.com/questions/815758/simple-serial-point-to-point-communication-protocol
* HDLC High-Level Data Link Control
  * High-Level Data Link Control (HDLC) is a bit-oriented code-transparent synchronous data link layer protocol developed by the International Organization for Standardization (ISO). The standard for HDLC is ISO/IEC 13239:2002. 
  * https://en.wikipedia.org/wiki/High-Level_Data_Link_Control
  * HDLC library for arduino , https://github.com/mengguang/ArduinoHDLC
* Modbus
  * Modbus is a serial communications protocol originally published by Modicon (now Schneider Electric) in 1979 for use with its programmable logic controllers (PLCs). Modbus has become a de facto standard communication protocol and is now a commonly available means of connecting industrial electronic devices.
  * https://en.wikipedia.org/wiki/Modbus
  * https://www.arduino.cc/en/ArduinoModbus/ArduinoModbus
