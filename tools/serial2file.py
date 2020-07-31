"""
Used for testng.
"""

import serial

ser = serial.Serial(
        port='/dev/ttyAMA0',
        baudrate = 9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS
)
with open('serial2file.bin', 'ab') as fout:
    while 1:
        x = ser.read(100)
        fout.write(x)
