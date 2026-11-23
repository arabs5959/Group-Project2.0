import sys
import types


class _FakeTime:

    def __init__(self):
        self._ms = 0

    def ticks_ms(self):
        return self._ms

    def ticks_add(self, base, delta):
        return base + delta

    def ticks_diff(self, a, b):
        return a - b

    def sleep_ms(self, ms):
        self._ms += ms

    def sleep(self, sec):
        self._ms += int(sec * 1000)


class _FakePin:
    def __init__(self, *args, **kwargs):
        pass


class _FakePWM:
    def __init__(self, *args, **kwargs):
        pass

    def freq(self, *args):
        pass

    def duty_u16(self, *args):
        pass


class _FakeUART:
    #In-memory UART double that supports outbound writes and inbound replies.

    def __init__(self, reply_bytes=b""):
        self.written = bytearray()
        self._incoming = bytearray(reply_bytes)

    def write(self, data):
        self.written.extend(data)
        return len(data)

    def any(self):
        return len(self._incoming) > 0

    def read(self):
        if not self._incoming:
            return None
        out = bytes(self._incoming)
        self._incoming.clear()
        return out


class _FakeADC:

    def __init__(self, raw_val):
        self.raw_val = raw_val

    def read(self, rate, channel):
        return self.raw_val

    def raw_to_v(self, raw):
        return raw * (4.096 / 32768.0)


def _install_micropython_stubs():
    if "machine" not in sys.modules:
        machine_mod = types.ModuleType("machine")
        machine_mod.__dict__["Pin"] = _FakePin
        machine_mod.__dict__["PWM"] = _FakePWM
        machine_mod.__dict__["UART"] = _FakeUART
        machine_mod.__dict__["I2C"] = object
        sys.modules["machine"] = machine_mod

    if "ads1x15" not in sys.modules:
        ads_mod = types.ModuleType("ads1x15")
        ads_mod.__dict__["ADS1015"] = _FakeADC
        sys.modules["ads1x15"] = ads_mod


_install_micropython_stubs()

import importlib.util  # noqa: E402
import Group_Project as p1  # noqa: E402

_spec = importlib.util.spec_from_file_location("second_pico", "Second pico(reader).py")
if _spec is None or _spec.loader is None:
    raise ImportError("Could not load 'Second pico(reader).py'")
p2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p2)


def assert_close(actual, expected, tol=1e-2, label=""):
    """Pass/fail helper for floating-point comparisons."""
    if abs(actual - expected) > tol:
        raise AssertionError(f"FAIL [{label}]: expected {expected} (+/-{tol}), got {actual}")
    print(f"PASS [{label}]: got {actual:.4f} (expected {expected:.4f})")


def test_duty_and_voltage_conversions():
    """Test 1: Duty u16 -> % and ADC raw -> V -> % of 3.3 V."""
    assert_close(p1.duty_u16_to_percent(0), 0.0, label="0% duty")
    assert_close(p1.duty_u16_to_percent(32768), 50.00076, label="50% duty")
    assert_close(p1.duty_u16_to_percent(65535), 100.0, label="100% duty")

    # 1.65 V out of 3.3 V is 50.0%; at gain=1 (4.096 V / 32768), 1.65 V is ~13200 counts
    fake_adc = _FakeADC(13200)
    volts, pct = p2.raw_to_percent_3v3(fake_adc, 13200, v_ref=3.3)
    assert_close(volts, 1.65, tol=0.01, label="ADS1015 raw_to_v at 1.65V")
    assert_close(pct, 50.0, tol=0.3, label="1.65V as % of 3.3V")


def test_line_framing_and_parsing():
    """Test 2: Newline-terminated UART message formatting and parsing."""
    line = p1.format_line_message(49.5)
    if not line.endswith("\n"):
        raise AssertionError("FAIL [newline framing]: message missing '\\n'")
    print("PASS [newline framing]: message ends with '\\n'")

    parsed = p1.parse_measured_percent(b"48.75\n")
    assert_close(parsed, 48.75, label="parse newline-terminated float")

    try:
        p1.parse_measured_percent(b"not_a_number\n")
        raise AssertionError("FAIL [invalid input]: expected ValueError")
    except ValueError:
        print("PASS [invalid input]: rejects non-numeric payload")


def test_uart_roundtrip_and_pico2_reader():
    """Test 3: Pico 2 reads framed line, waits settle time, and replies with '\\n'."""
    fake_time = _FakeTime()
    p2.time = fake_time
    p1.time = fake_time

    uart2 = _FakeUART(reply_bytes=b"50.25\n")
    buf = bytearray()
    cmd = p2.read_incoming_line(uart2, buf)
    if cmd != "50.25":
        raise AssertionError(f"FAIL [Pico 2 line read]: expected '50.25', got {cmd!r}")
    print("PASS [Pico 2 line read]: extracted complete line '50.25'")

    uart2_out = _FakeUART()
    fake_adc = _FakeADC(13200)
    _, measured_pct = p2.measure_filtered_duty_percent(fake_adc, settle_s=1.6)
    if fake_time._ms < 1600:
        raise AssertionError(f"FAIL [settle time]: expected >=1600 ms elapsed, got {fake_time._ms}")
    print(f"PASS [settle time]: waited {fake_time._ms} ms (>= 1600 ms)")

    p2.send_percent_reply(uart2_out, measured_pct)
    sent_str = bytes(uart2_out.written).decode("utf-8")
    if not sent_str.endswith("\n"):
        raise AssertionError(f"FAIL [Pico 2 reply]: missing '\\n' in {sent_str!r}")
    print(f"PASS [Pico 2 reply]: sent newline-terminated reply {sent_str!r}")


def run_test_harness():
    """Execute all unit tests and report summary."""
    tests = [
        test_duty_and_voltage_conversions,
        test_line_framing_and_parsing,
        test_uart_roundtrip_and_pico2_reader,
    ]
    passed = 0
    for test_fn in tests:
        test_fn()
        passed += 1
    print(f"\nTEST HARNESS COMPLETE: {passed}/{len(tests)} test suites PASSED.")


if __name__ == "__main__":
    run_test_harness()
