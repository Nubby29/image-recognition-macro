# Image Recognition Macro v0.2.0

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import pyautogui


@dataclass
class DetectionResult:
    x: int
    y: int
    width: int
    height: int
    confidence: float


class ImageDetector:
    """Whole-screen image detector using OpenCV template matching."""

    def __init__(self, threshold: float = 0.80):
        self.threshold = threshold

    def screenshot(self) -> np.ndarray:
        image = pyautogui.screenshot()
        rgb = np.asarray(image)
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    def find(
        self,
        template_path: str | Path,
        screen: Optional[np.ndarray] = None,
        threshold: Optional[float] = None,
    ) -> Optional[DetectionResult]:
        template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
        if template is None:
            raise FileNotFoundError(f"Could not read template: {template_path}")

        if screen is None:
            screen = self.screenshot()

        th = self.threshold if threshold is None else threshold
        sh, sw = screen.shape[:2]
        thh, thw = template.shape[:2]

        if thh > sh or thw > sw:
            return None

        # Grayscale matching is less sensitive to display rendering differences
        # and substantially cheaper than matching all three color channels.
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        result = cv2.matchTemplate(
            screen_gray, template_gray, cv2.TM_CCOEFF_NORMED
        )
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if float(max_val) < th:
            return None

        x, y = max_loc
        return DetectionResult(
            x=x + thw // 2,
            y=y + thh // 2,
            width=thw,
            height=thh,
            confidence=float(max_val),
        )
