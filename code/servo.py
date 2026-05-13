import threading

from gpiozero import AngularServo
from gpiozero.pins.lgpio import LGPIOFactory


class TiltServoController:
    """Servo controller for vertical tilt."""

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
        self.factory = None
        self.servo = None
        self.zero_offset = zero_offset
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.current_relative_angle = 0.0
        self.detach_after_move = detach_after_move
        self.settle_time = settle_time
        self._detach_timer = None
        self._lock = threading.Lock()
        self._target_angle = None
        self._worker_event = threading.Event()
        self._closed = False
        self._worker_thread = threading.Thread(target=self._servo_worker, daemon=True)
        self._worker_thread.start()

        try:
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
            physical_angle = max(
                self.min_angle,
                min(self.max_angle, self.zero_offset + relative_angle),
            )
            self.current_relative_angle = physical_angle - self.zero_offset
            self._queue_angle(physical_angle)
        except Exception as exc:
            print(f"[Servo] set angle failed: {exc}")

    def _queue_angle(self, physical_angle):
        with self._lock:
            self._target_angle = physical_angle
        self._worker_event.set()

    def _servo_worker(self):
        while True:
            self._worker_event.wait()
            if self._closed:
                return

            with self._lock:
                physical_angle = self._target_angle
                self._target_angle = None
                self._worker_event.clear()

            if physical_angle is None:
                continue

            try:
                with self._lock:
                    if self.servo is not None:
                        self.servo.angle = physical_angle
                if self.detach_after_move:
                    self._schedule_detach()
            except Exception as exc:
                print(f"[Servo] set angle failed: {exc}")

    def _schedule_detach(self):
        if self._detach_timer is not None:
            self._detach_timer.cancel()
        self._detach_timer = threading.Timer(self.settle_time, self.stop)
        self._detach_timer.daemon = True
        self._detach_timer.start()

    def adjust_relative_angle(self, delta):
        self.set_relative_angle(self.current_relative_angle + delta)

    def set_position(self, pos):
        # Keep compatibility with earlier -1.0~1.0 API.
        pos = max(-1.0, min(1.0, pos))
        self.set_relative_angle(pos * 90.0)

    def stop(self):
        with self._lock:
            if self.servo is not None:
                self.servo.angle = None

    def close(self):
        self._closed = True
        self._worker_event.set()
        if self._detach_timer is not None:
            self._detach_timer.cancel()
            self._detach_timer = None
        self.stop()
        print("[Servo] closed")
