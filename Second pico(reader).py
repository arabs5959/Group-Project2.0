
#Waits in a loop for a desired duty cycle (%) over UART from Pico 1, waits
#1.6 s for the RC low-pass filter to settle, reads the ADS1015 channel,
#converts raw ADC counts -> volts -> percentage of 3.3 V, logs the comparison,
#and sends the measured percentage back over UART terminated with '\\n'.


import time
from machine import I2C, Pin, UART
from ads1x15 import ADS1015


I2C_ID = 1
I2C_SDA_PIN = 14
I2C_SCL_PIN = 15
ADS1015_ADDR = 0x48
ADS1015_GAIN = 1
ADS1015_RATE = 4
ADS1015_PWM_CH = 2

FILTER_SETTLE_S = 1.6
REFERENCE_VOLTAGE = 3.3

UART_ID = 1
UART_BAUD = 9600
UART_TX_PIN = 8
UART_RX_PIN = 9


def setup_adc(i2c_id=I2C_ID, sda_pin=I2C_SDA_PIN, scl_pin=I2C_SCL_PIN, addr=ADS1015_ADDR, gain=ADS1015_GAIN):
    """Initialize I2C bus and ADS1015 ADC instance."""
    i2c = I2C(i2c_id, sda=Pin(sda_pin), scl=Pin(scl_pin))
    devices = i2c.scan()
    print("[Pico 2] I2C devices found:", [hex(d) for d in devices])
    return ADS1015(i2c, addr, gain)


def setup_uart(uart_id=UART_ID, baudrate=UART_BAUD, tx_pin=UART_TX_PIN, rx_pin=UART_RX_PIN):
    #Initialize UART communication.
    return UART(
        uart_id,
        baudrate=baudrate,
        tx=Pin(tx_pin),
        rx=Pin(rx_pin),
        bits=8,
        parity=None,
        stop=1,
    )


def raw_to_percent_3v3(adc, raw_value, v_ref=REFERENCE_VOLTAGE):
    #Convert raw ADS1015 reading -> volts (via raw_to_v) -> % of 3.3 V.
    volts = adc.raw_to_v(raw_value)
    pct = (volts / v_ref) * 100.0
    return volts, pct


def measure_filtered_duty_percent(adc, channel=ADS1015_PWM_CH, rate=ADS1015_RATE, settle_s=FILTER_SETTLE_S):
    """Wait for filter settling time, then read ADS1015 and return (volts, pct)."""
    time.sleep(settle_s)
    raw_val = adc.read(rate, channel)
    return raw_to_percent_3v3(adc, raw_val)


def read_incoming_line(uart, line_buf):
    """
    Append available UART bytes into line_buf (bytearray).
    If a '\\n'-terminated line is complete, return the decoded line and clear
    the consumed portion; otherwise return None.
    """
    if uart.any():
        chunk = uart.read()
        if chunk:
            line_buf.extend(chunk)

    if b"\n" in line_buf:
        raw_line, _, remainder = bytes(line_buf).partition(b"\n")
        line_buf[:] = remainder
        return raw_line.decode("utf-8", "ignore").strip()

    return None


def send_percent_reply(uart, measured_pct):
    """Send measured percentage back to Pico 1 as '<value>\\n'."""
    msg = f"{measured_pct:.2f}\n"
    uart.write(msg.encode("utf-8"))


def serve_loop():
    """Continuously listen for desired duty (%) commands and reply with measured (%)."""
    adc = setup_adc()
    uart = setup_uart()
    line_buf = bytearray()

    print("[Pico 2] Ready and waiting for duty cycle commands over UART...")

    while True:
        cmd_text = read_incoming_line(uart, line_buf)
        if cmd_text:
            try:
                desired_pct = float(cmd_text)
            except ValueError:
                print(f"[Pico 2][Warn] Ignored non-numeric UART input: {cmd_text!r}")
                continue

            volts, measured_pct = measure_filtered_duty_percent(adc)
            diff = measured_pct - desired_pct
            print(
                f"[Pico 2] Desired: {desired_pct:.2f}% | "
                f"ADC V: {volts:.3f} V -> Measured: {measured_pct:.2f}% | "
                f"Diff: {diff:+.2f}%"
            )
            send_percent_reply(uart, measured_pct)

        time.sleep_ms(20)


if __name__ == "__main__":
    serve_loop()
