from machine import I2C, Pin
from ads1x15 import ADS1015


I2C_SDA_PIN = 14
I2C_SCL_PIN = 15
ADS1015_ADDR = 0x48
ADS1015_PWM_CH = 2
REFERENCE_VOLTAGE = 3.3


def main():
    #Scan I2C bus and print raw counts, voltage, and % of 3.3 V.
    i2c = I2C(1, sda=Pin(I2C_SDA_PIN), scl=Pin(I2C_SCL_PIN))
    print("I2C scan:", [hex(addr) for addr in i2c.scan()])

    adc = ADS1015(i2c, ADS1015_ADDR, 1)
    raw = adc.read(4, ADS1015_PWM_CH)
    volts = adc.raw_to_v(raw)
    pct = (volts / REFERENCE_VOLTAGE) * 100.0
    print(f"raw={raw}, voltage={volts:.3f} V, duty_pct={pct:.2f}%")


if __name__ == "__main__":
    main()
