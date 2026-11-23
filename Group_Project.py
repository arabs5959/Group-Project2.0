

#Sets a PWM duty cycle on Pico 1, sends the desired duty cycle (in %) over
#UART to Pico 2, waits for Pico 2's measured percentage reply, and displays
#the comparison and difference.


import time
from machine import Pin, PWM, UART


PWM_OUT_PIN = 11
PWM_FREQ_HZ = 50
UART_ID = 1
UART_BAUD = 9600
UART_TX_PIN = 8
UART_RX_PIN = 9
REPLY_TIMEOUT_S = 5.0


def duty_u16_to_percent(duty_u16):
    """Convert a 16-bit MicroPython PWM duty value (0..65535) to 0..100%."""
    if duty_u16 < 0 or duty_u16 > 65535:
        raise ValueError("duty_u16 must be between 0 and 65535")
    return (duty_u16 / 65535.0) * 100.0


def voltage_to_percent_3v3(voltage):
    """Convert a measured voltage into percentage of the 3.3 V logic rail."""
    return (voltage / 3.3) * 100.0


def format_line_message(value):
    """Format a numeric value as a newline-terminated ASCII string for UART."""
    return f"{value}\n"


def parse_measured_percent(raw_line):
    """Parse a received UART line into a float percentage, or None if invalid."""
    if not raw_line:
        return None
    text = raw_line.decode("utf-8", "ignore").strip()
    if not text:
        return None
    return float(text)


def setup_pwm(pin_num=PWM_OUT_PIN, freq_hz=PWM_FREQ_HZ, duty_u16=32768):
    """Initialize and start a PWM signal on the specified GPIO pin."""
    pwm_pin = PWM(Pin(pin_num))
    pwm_pin.freq(freq_hz)
    pwm_pin.duty_u16(duty_u16)
    return pwm_pin


def setup_uart(uart_id=UART_ID, baudrate=UART_BAUD, tx_pin=UART_TX_PIN, rx_pin=UART_RX_PIN):
    """Initialize UART communication."""
    return UART(
        uart_id,
        baudrate=baudrate,
        tx=Pin(tx_pin),
        rx=Pin(rx_pin),
        bits=8,
        parity=None,
        stop=1,
    )


def send_and_receive_duty_percent(uart, desired_pct, timeout_s=REPLY_TIMEOUT_S):
   
    #Send desired_pct ('<val>\\n') over UART and wait for Pico 2's measured
    #percentage reply ('<val>\\n'). Returns measured_pct or None on timeout.

    payload = format_line_message(round(desired_pct, 2))
    uart.write(payload.encode("utf-8"))

    deadline = time.ticks_add(time.ticks_ms(), int(timeout_s * 1000))
    buffer = bytearray()

    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        if uart.any():
            chunk = uart.read()
            if chunk:
                buffer.extend(chunk)
                if b"\n" in buffer:
                    line, _, _ = bytes(buffer).partition(b"\n")
                    return parse_measured_percent(line + b"\n")
        time.sleep_ms(20)

    return None


def report_comparison(desired_pct, measured_pct):
    """Print desired duty (%), measured duty (%), and signed/absolute difference."""
    if measured_pct is None:
        print(f"[Warn] Desired: {desired_pct:.2f}% | No valid reply received from Pico 2.")
        return

    diff = measured_pct - desired_pct
    print(
        f"Desired: {desired_pct:.2f}% | Measured: {measured_pct:.2f}% | "
        f"Difference (Measured - Desired): {diff:+.2f}%"
    )


def run_monitor(test_duties_u16=(16384, 32768, 49152)):
    """Run PWM generation and comparison across one or more duty cycle settings."""
    pwm = setup_pwm(PWM_OUT_PIN, PWM_FREQ_HZ, test_duties_u16[0])
    uart = setup_uart()

    for duty_u16 in test_duties_u16:
        pwm.duty_u16(duty_u16)
        desired_pct = duty_u16_to_percent(duty_u16)
        print(f"[Pico 1] Set PWM duty to {duty_u16} ({desired_pct:.2f}%)")

        # Allow filter + Pico 2 settle + measurement time before timing out
        measured_pct = send_and_receive_duty_percent(uart, desired_pct, timeout_s=5.0)
        report_comparison(desired_pct, measured_pct)
        time.sleep(0.5)


if __name__ == "__main__":
    run_monitor()
