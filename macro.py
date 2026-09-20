# Image Recognition Macro v0.5.0

from dataclasses import dataclass
import threading
import time
from typing import Callable, Optional

import pyautogui

from detector import DetectionRegion, ImageDetector, DetectionResult


@dataclass
class MacroSettings:
    threshold: float = 0.80
    scan_interval: float = 0.20
    click_delay: float = 0.15


class MacroRunner:
    """Small MVP runner; the full visual macro editor comes later."""

    def __init__(self, detector: ImageDetector, settings: MacroSettings):
        self.detector = detector
        self.settings = settings
        self._stop = threading.Event()
        self.running = False

    def stop(self) -> None:
        self._stop.set()

    def run_detect_click_loop(
        self,
        template_path: str,
        on_status: Callable[[str], None],
        max_iterations: Optional[int] = None,
        region: Optional[DetectionRegion] = None,
    ) -> None:
        self._stop.clear()
        self.running = True
        iterations = 0

        try:
            while not self._stop.is_set():
                result: Optional[DetectionResult] = self.detector.find(
                    template_path,
                    threshold=self.settings.threshold,
                    region=region,
                )

                if result:
                    on_status(
                        f"FOUND  x={result.x}  y={result.y}  "
                        f"confidence={result.confidence:.3f}"
                    )
                    pyautogui.click(result.x, result.y)
                    time.sleep(self.settings.click_delay)
                    iterations += 1
                else:
                    on_status("SEARCHING — target not found")
                    time.sleep(self.settings.scan_interval)

                if max_iterations is not None and iterations >= max_iterations:
                    break
        finally:
            self.running = False
            on_status("STOPPED")
