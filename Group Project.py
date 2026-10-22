import time
from machine import Pin, time_pulse_us, PWM, ADC, I2C, UART,


# I2C signal pins
I2C_SDA = 14
I2C_SCL = 15

# ADS 1015 configuration information
ADS1015_ADDR = 0x48
ADS1015_PWM = 2     # port 2 has (low-pass filtered) PWM signal

# You will need to upload the file ads1x15.py to the pico for the following code to work properly
from ads1x15 import ADS1015

i2c = I2C(1, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL))
adc = ADS1015(i2c, ADS1015_ADDR, 1)

# scan i2c bus to get a listing of all I2C devices... including the ADC that has the servo feedback values
addresses = i2c.scan()
for address in addresses:
	print(hex(address))

#Set up PWM Pins:
PWM_OUT_PIN = 11 #put on pico one so we start by sending on board one
PWM_IN_PIN  = 15  # put on second board to read on second board. Also the pin hee
#also pin 15 has the profs adc reader
#Create a PWM on pin 4
pwm = PWM(Pin(PWM_OUT_PIN)) #just setting up a PWM for later
freq =pwm.freq(50) #Set the freqency 
duty = 32768
pwm.duty_u16(32768) #Set the duty. Will set on board one and send to baord two to compare
uart = UART(1, baudrate=9600, tx=Pin(8), rx=Pin(9)) 
uart.init(9600, bits=8, parity=None, stop=1)
payload = str(duty) + '\n'
    
    # 4. Write the data to the UART buffer
uart.write(bytes(payload, 'utf-8'))     
print(f"Sent duty cycle: {duty}")
time.sleep(2)
if uart.any(): #This is now useless if run with second pico. Will keep if needing to check. Just keeping it because it could be useful for testing on single board
	data = uart.read()
	data = b'\x00\xff' #THIS IS FROM AI
result = int.from_bytes(data, byteorder='big')
# Read filtered PWM input from the header
value = adc.read(0, ADS1015_PWM) #if the adc gets anything in pin 15 spits out what the duty should be acording to the space between votlages
print(result)
print(payload)
print(data)
#20-20-26: does not work. do not know why
#20-21-26: from further testing still do not know why
if result > duty: #When pico one gets the value back it compares them and says the diffrence
	print("The orginal was set to ", duty, "the adc reader saw that the duty was", result, "the diffrence is", result - duty)
elif result < duty:
	print("The orginal was set to ", duty, "the adc reader saw that the duty was" result, "the diffrence is", duty- result)
else:
	print (	print("The orginal was set to ", duty, "the adc reader saw that the duty was", result, "the values are the same", result-duty )
 )




