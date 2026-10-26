import time
from machine import Pin, time_pulse_us, PWM, ADC, I2C, UART,
# I2C signal pins
I2C_SDA = 14
I2C_SCL = 15

# ADS 1015 configuration information
ADS1015_ADDR = 0x48
ADS1015_PWM = 2     # port 2 has (low-pass filtered) PWM signal

from machine import Pin, ADC, I2C
# You will need to upload the file ads1x15.py to the pico for the following code to work properly
from ads1x15 import ADS1015

i2c = I2C(1, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL))
adc = ADS1015(i2c, ADS1015_ADDR, 1)

# scan i2c bus to get a listing of all I2C devices... including the ADC that has the servo feedback values
addresses = i2c.scan()
for address in addresses:
	print(hex(address))


uart = UART(1, baudrate=9600, tx=Pin(8), rx=Pin(9)) 
uart.init(9600, bits=8, parity=None, stop=1)

value = adc.read(0, ADS1015_PWM) #if the adc gets anything in pin 15 spits out what the duty should be acording to the space between votlages

def raw_to_percent (value):
	return (value / 65535 * 100)

raw_to_percent(value)
data = -1
if uart.any(): #This is now useless if run with second pico. Will keep if needing to check. Just keeping it because it could be useful for testing on single board
	data = uart.read()
	data = b'\x00\xff' #THIS IS FROM AI
result = int.from_bytes(data if isinstance(data, bytes) else b'', 'big')
# Read filtered PWM input from the header
#value = adc.read(0, ADS1015_PWM) #if the adc gets anything in pin 15 spits out what the duty should be acording to the space between votlages
print("[Debug] result = ",
 result)
print("[Debug] data = ",
 data)
# Read filtered PWM input from the header
uart.write(value)
print(value)
print(data)
