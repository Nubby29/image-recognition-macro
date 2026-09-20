# Image Recognition Macro v0.5.0

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


@dataclass
class DetectionRegion:
    x: int
    y: int
    width: int
    height: int


class ImageDetector:
    """Image detector using OpenCV template matching, optionally inside a screen region."""

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
        region: Optional[DetectionRegion] = None,
    ) -> Optional[DetectionResult]:
        template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
        if template is None:
            raise FileNotFoundError(f"Could not read template: {template_path}")

        if screen is None:
            screen = self.screenshot()

        th = self.threshold if threshold is None else threshold

        offset_x = 0
        offset_y = 0

        if region is not None:
            screen_h, screen_w = screen.shape[:2]
            x1 = max(0, min(region.x, screen_w))
            y1 = max(0, min(region.y, screen_h))
            x2 = max(x1, min(region.x + region.width, screen_w))
            y2 = max(y1, min(region.y + region.height, screen_h))

            if x2 <= x1 or y2 <= y1:
                return None

            screen = screen[y1:y2, x1:x2]
            offset_x = x1
            offset_y = y1

        sh, sw = screen.shape[:2]
        thh, thw = template.shape[:2]

        if thh > sh or thw > sw:
            return None

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
            x=offset_x + x + thw // 2,
            y=offset_y + y + thh // 2,
            width=thw,
            height=thh,
            confidence=float(max_val),
        )
