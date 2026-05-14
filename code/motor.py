import time
import lgpio

class DCMotorController:
    """控制水平旋轉的雙向直流馬達控制器。"""

    # 角度與馬達通電時間的校正表，用來把目標旋轉角度換算成運轉秒數。
    DEFAULT_CALIBRATION = [
        (0.0, 0.0),
        (5.0, 0.0370),
        (10.0, 0.0555),
        (15.0, 0.0740),
        (20.0, 0.0925),
        (25.0, 0.1110),
        (30.0, 0.1295),
        (35.0, 0.1480),
        (40.0, 0.1665),
        (45.0, 0.1850),
        (50.0, 0.2035),
        (55.0, 0.2220),
        (60.0, 0.2405),
        (65.0, 0.2590),
        (70.0, 0.2775),
        (75.0, 0.2960),
        (80.0, 0.3145),
    ]

    def __init__(
        self,
        pin=None,
        in1_pin=17,
        in2_pin=27,
        frequency=1000,
        default_speed=35,
        calibration=None,
    ):
        # 保留舊版單腳位用法的相容性；如果有傳入 pin，就當作 in1_pin 使用。
        if pin is not None:
            in1_pin = pin

        self.in1_pin = in1_pin
        self.in2_pin = in2_pin
        self.frequency = frequency
        self.default_speed = default_speed
        self.calibration = calibration or self.DEFAULT_CALIBRATION
        self.h = None

        try:
            # 開啟預設 GPIO chip，並將馬達控制腳位設定為輸出模式。
            self.h = lgpio.gpiochip_open(0)
            lgpio.gpio_claim_output(self.h, self.in1_pin)
            if self.in2_pin is not None:
                lgpio.gpio_claim_output(self.h, self.in2_pin)
            print(
                f"[Motor] initialized on GPIO {self.in1_pin}"
                + (f" and GPIO {self.in2_pin}" if self.in2_pin is not None else "")
            )
        except Exception as exc:
            print(f"[Motor] initialization failed: {exc}")

    def _calculate_run_time(self, angle):
        # 只計算需要運轉多久；方向會在 rotate() 依照角度正負號判斷。
        angle = abs(float(angle))
        if angle <= 0:
            return 0.0

        if angle >= self.calibration[-1][0]:
            # 超過校正表最大角度時，沿用最後兩個校正點的斜率做線性外推。
            max_angle, max_time = self.calibration[-1]
            prev_angle, prev_time = self.calibration[-2]
            slope = (max_time - prev_time) / (max_angle - prev_angle)
            return max_time + (angle - max_angle) * slope

        for index in range(len(self.calibration) - 1):
            low_angle, low_time = self.calibration[index]
            high_angle, high_time = self.calibration[index + 1]
            if low_angle <= angle <= high_angle:
                # 角度落在兩個校正點之間時，使用線性插值估算運轉時間。
                ratio = (angle - low_angle) / (high_angle - low_angle)
                return low_time + ratio * (high_time - low_time)

        return 0.0

    def run(self, speed=None, direction=1):
        if self.h is None:
            return

        # 將速度限制在 PWM duty cycle 的合法範圍 0~100。
        duty_cycle = max(0, min(100, speed if speed is not None else self.default_speed))

        try:
            if self.in2_pin is None:
                # 單腳位模式只輸出 PWM，適合舊版接線或單向控制。
                lgpio.tx_pwm(self.h, self.in1_pin, self.frequency, duty_cycle)
                return

            if direction >= 0:
                # 雙腳位模式透過 IN1/IN2 一邊輸出 PWM、一邊歸零來切換方向。
                lgpio.tx_pwm(self.h, self.in1_pin, self.frequency, duty_cycle)
                lgpio.tx_pwm(self.h, self.in2_pin, self.frequency, 0)
            else:
                lgpio.tx_pwm(self.h, self.in1_pin, self.frequency, 0)
                lgpio.tx_pwm(self.h, self.in2_pin, self.frequency, duty_cycle)
        except Exception as exc:
            print(f"[Motor] run failed: {exc}")

    def stop(self):
        if self.h is None:
            return

        try:
            # 將 PWM duty cycle 歸零即可停止馬達輸出。
            lgpio.tx_pwm(self.h, self.in1_pin, self.frequency, 0)
            if self.in2_pin is not None:
                lgpio.tx_pwm(self.h, self.in2_pin, self.frequency, 0)
        except Exception:
            pass

    def rotate(self, angle, speed=None):
        run_time = self._calculate_run_time(angle)
        if run_time <= 0:
            return

        # 依角度正負決定旋轉方向，通電指定時間後立即停止。
        direction = 1 if angle >= 0 else -1
        self.run(speed=speed, direction=direction)
        time.sleep(run_time)
        self.stop()

    def nudge_left(self, angle=5, speed=None):
        # 小幅向左修正，角度固定轉成負值以符合 rotate() 的方向判斷。
        self.rotate(-abs(angle), speed=speed)

    def nudge_right(self, angle=5, speed=None):
        # 小幅向右修正，角度固定轉成正值以符合 rotate() 的方向判斷。
        self.rotate(abs(angle), speed=speed)

    def rotate_30_degrees(self, speed=50, rotate_time=0.1):
        # 保留舊測試使用的介面，直接以固定時間驅動馬達。
        self.run(speed=speed, direction=1)
        time.sleep(rotate_time)
        self.stop()

    def close(self):
        # 關閉前先停止馬達，避免釋放 GPIO 後仍有輸出殘留。
        self.stop()
        if self.h is None:
            return
        try:
            lgpio.gpiochip_close(self.h)
            print("[Motor] closed")
        except Exception:
            pass
