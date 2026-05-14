import threading

from gpiozero import AngularServo
from gpiozero.pins.lgpio import LGPIOFactory


class TiltServoController:
    """控制垂直俯仰角度的伺服馬達控制器。"""

    def __init__(
        self,
        pin=12,
        zero_offset=90,
        min_angle=0,
        max_angle=180,
        min_pulse_width=0.5 / 1000,
        max_pulse_width=2.5 / 1000,
        detach_after_move=True,
        settle_time=0.25,
    ):
        # factory/servo 在初始化失敗時保留 None，讓後續呼叫可以安全返回。
        self.factory = None
        self.servo = None
        self.zero_offset = zero_offset
        self.min_angle = min_angle
        self.max_angle = max_angle
        # 對外使用相對角度；實際輸出角度會再加上 zero_offset。
        self.current_relative_angle = 0.0
        self.detach_after_move = detach_after_move
        self.settle_time = settle_time
        self._detach_timer = None
        self._lock = threading.Lock()
        # 只保存最新目標角度，背景執行緒會在被喚醒後送到伺服馬達。
        self._target_angle = None
        self._worker_event = threading.Event()
        self._closed = False
        # 用背景執行緒處理角度輸出，避免主流程因伺服馬達動作而卡住。
        self._worker_thread = threading.Thread(target=self._servo_worker, daemon=True)
        self._worker_thread.start()

        try:
            # 使用 lgpio pin factory，讓 gpiozero 能透過 LGPIO 控制 Raspberry Pi GPIO。
            self.factory = LGPIOFactory()
            self.servo = AngularServo(
                pin,
                initial_angle=None,
                min_angle=min_angle,
                max_angle=max_angle,
                min_pulse_width=min_pulse_width,
                max_pulse_width=max_pulse_width,
                pin_factory=self.factory,
            )
            self._queue_angle(zero_offset)
            print(f"[Servo] initialized on GPIO {pin}, zero offset {zero_offset}")
        except Exception as exc:
            print(f"[Servo] initialization failed: {exc}")

    def set_relative_angle(self, relative_angle):
        if self.servo is None:
            return

        try:
            # 將相對角度轉成實體角度，並限制在伺服馬達允許的範圍內。
            physical_angle = max(
                self.min_angle,
                min(self.max_angle, self.zero_offset + relative_angle),
            )
            self.current_relative_angle = physical_angle - self.zero_offset
            self._queue_angle(physical_angle)
        except Exception as exc:
            print(f"[Servo] set angle failed: {exc}")

    def _queue_angle(self, physical_angle):
        # 更新目標角度後喚醒背景執行緒；連續命令時只會執行最新角度。
        with self._lock:
            self._target_angle = physical_angle
        self._worker_event.set()

    def _servo_worker(self):
        while True:
            # 等待新的角度命令；close() 也會喚醒此事件讓執行緒可以結束。
            self._worker_event.wait()
            if self._closed:
                return

            with self._lock:
                # 取出目前最新目標角度，並清空事件狀態等待下一次命令。
                physical_angle = self._target_angle
                self._target_angle = None
                self._worker_event.clear()

            if physical_angle is None:
                continue

            try:
                with self._lock:
                    if self.servo is not None:
                        # 實際寫入 AngularServo.angle，開始讓伺服馬達移動。
                        self.servo.angle = physical_angle
                if self.detach_after_move:
                    self._schedule_detach()
            except Exception as exc:
                print(f"[Servo] set angle failed: {exc}")

    def _schedule_detach(self):
        # 重新排程自動釋放，避免伺服馬達長時間保持出力造成抖動或發熱。
        if self._detach_timer is not None:
            self._detach_timer.cancel()
        self._detach_timer = threading.Timer(self.settle_time, self.stop)
        self._detach_timer.daemon = True
        self._detach_timer.start()

    def adjust_relative_angle(self, delta):
        self.set_relative_angle(self.current_relative_angle + delta)

    def set_position(self, pos):
        # 保留舊版 -1.0~1.0 位置 API，並映射成 -90~90 度的相對角度。
        pos = max(-1.0, min(1.0, pos))
        self.set_relative_angle(pos * 90.0)

    def stop(self):
        # 將 angle 設為 None 會讓 gpiozero 停止輸出 PWM，等同釋放伺服馬達。
        with self._lock:
            if self.servo is not None:
                self.servo.angle = None

    def close(self):
        # 通知背景執行緒結束，取消尚未觸發的釋放計時器，最後停止 PWM 輸出。
        self._closed = True
        self._worker_event.set()
        if self._detach_timer is not None:
            self._detach_timer.cancel()
            self._detach_timer = None
        self.stop()
        print("[Servo] closed")
