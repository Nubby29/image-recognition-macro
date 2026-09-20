# Image Recognition Macro v0.2.0

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from detector import ImageDetector
from macro import MacroRunner, MacroSettings


APP_VERSION = "0.2.0"


class ImageMacroApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"Image Recognition Macro v{APP_VERSION}")
        self.root.geometry("760x560")
        self.root.minsize(680, 500)

        self.template_path: str | None = None
        self.detector = ImageDetector()
        self.runner = MacroRunner(self.detector, MacroSettings())
        self.worker: threading.Thread | None = None

        self.threshold = tk.DoubleVar(value=0.80)
        self.interval = tk.DoubleVar(value=0.20)
        self.status = tk.StringVar(value="READY")

        self._build_ui()

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer, text="Image Recognition Macro",
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        ttk.Label(
            outer, text="Windows MVP • detect anywhere on screen, then click",
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 18))

        template_box = ttk.LabelFrame(outer, text="1. Target Image", padding=14)
        template_box.pack(fill="x", pady=(0, 12))

        self.template_label = ttk.Label(
            template_box, text="No template selected"
        )
        self.template_label.pack(side="left", fill="x", expand=True)

        ttk.Button(
            template_box, text="Select Image", command=self.select_template
        ).pack(side="right")

        settings_box = ttk.LabelFrame(outer, text="2. Detection Settings", padding=14)
        settings_box.pack(fill="x", pady=(0, 12))

        ttk.Label(settings_box, text="Confidence").grid(row=0, column=0, sticky="w")
        ttk.Scale(
            settings_box, from_=0.50, to=0.99, variable=self.threshold,
            orient="horizontal", length=240
        ).grid(row=0, column=1, padx=10, sticky="ew")
        self.threshold_value = ttk.Label(settings_box, text="0.80")
        self.threshold_value.grid(row=0, column=2, sticky="w")

        ttk.Label(settings_box, text="Search interval (sec)").grid(
            row=1, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Spinbox(
            settings_box, from_=0.05, to=5.0, increment=0.05,
            textvariable=self.interval, width=10
        ).grid(row=1, column=1, padx=10, sticky="w", pady=(10, 0))

        settings_box.columnconfigure(1, weight=1)
        self.threshold.trace_add("write", self._update_threshold_label)

        test_box = ttk.LabelFrame(outer, text="3. Test", padding=14)
        test_box.pack(fill="x", pady=(0, 12))

        ttk.Button(
            test_box, text="Detect Once", command=self.detect_once
        ).pack(side="left")

        ttk.Button(
            test_box, text="Detect + Click", command=self.detect_and_click
        ).pack(side="left", padx=8)

        ttk.Button(
            test_box, text="Run Loop", command=self.start_loop
        ).pack(side="left")

        ttk.Button(
            test_box, text="STOP (F8)", command=self.stop_loop
        ).pack(side="right")

        status_box = ttk.LabelFrame(outer, text="Status", padding=14)
        status_box.pack(fill="both", expand=True)

        ttk.Label(
            status_box, textvariable=self.status,
            font=("Consolas", 11), wraplength=680
        ).pack(anchor="nw")

        ttk.Label(
            outer,
            text="Tip: move the target around the screen. Detection uses the current screenshot, not saved coordinates.",
            foreground="#555555"
        ).pack(anchor="w", pady=(10, 0))

        self.root.bind("<F8>", lambda _event: self.stop_loop())

    def _update_threshold_label(self, *_):
        self.threshold_value.config(text=f"{self.threshold.get():.2f}")

    def select_template(self):
        path = filedialog.askopenfilename(
            title="Select target image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.webp"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.template_path = path
            self.template_label.config(text=Path(path).name)
            self.status.set("TEMPLATE SELECTED — ready to detect")

    def _prepare(self) -> bool:
        if not self.template_path:
            messagebox.showwarning("No template", "Select a target image first.")
            return False
        self.detector.threshold = self.threshold.get()
        self.runner.settings.threshold = self.threshold.get()
        try:
            self.runner.settings.scan_interval = max(0.05, float(self.interval.get()))
        except (TypeError, ValueError):
            self.runner.settings.scan_interval = 0.20
        return True

    def detect_once(self):
        if not self._prepare():
            return
        self.status.set("CAPTURING SCREEN...")
        try:
            result = self.detector.find(
                self.template_path, threshold=self.threshold.get()
            )
        except Exception as exc:
            self.status.set(f"ERROR: {exc}")
            return

        if result:
            self.status.set(
                f"FOUND — center=({result.x}, {result.y})  "
                f"size={result.width}x{result.height}  "
                f"confidence={result.confidence:.3f}"
            )
        else:
            self.status.set(
                f"NOT FOUND — no match reached {self.threshold.get():.2f}"
            )

    def detect_and_click(self):
        if not self._prepare():
            return
        self.status.set("CAPTURING SCREEN...")
        try:
            result = self.detector.find(
                self.template_path, threshold=self.threshold.get()
            )
        except Exception as exc:
            self.status.set(f"ERROR: {exc}")
            return

        if result:
            import pyautogui
            pyautogui.click(result.x, result.y)
            self.status.set(
                f"CLICKED — ({result.x}, {result.y})  "
                f"confidence={result.confidence:.3f}"
            )
        else:
            self.status.set("NOT FOUND — nothing clicked")

    def start_loop(self):
        if not self._prepare():
            return
        if self.runner.running:
            self.status.set("ALREADY RUNNING")
            return

        self.status.set("STARTING LOOP...")
        self.worker = threading.Thread(
            target=self.runner.run_detect_click_loop,
            args=(self.template_path, self.status.set),
            daemon=True,
        )
        self.worker.start()

    def stop_loop(self):
        self.runner.stop()
        self.status.set("STOP REQUESTED")


def main():
    root = tk.Tk()
    ImageMacroApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
