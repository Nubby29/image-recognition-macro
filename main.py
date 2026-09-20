# Image Recognition Macro v0.5.0

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from detector import DetectionRegion, ImageDetector
from macro import MacroRunner, MacroSettings


APP_VERSION = "0.5.0"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


class RegionSelector(tk.Toplevel):
    """Fullscreen screenshot viewer where the user can drag a detection region."""

    def __init__(self, parent, screenshot_image, on_selected):
        super().__init__(parent)
        self.parent = parent
        self.on_selected = on_selected
        self.image = screenshot_image
        self.photo = ImageTk.PhotoImage(self.image)

        self.title("Select Detection Region")
        self.attributes("-topmost", True)
        self.resizable(False, False)

        self.canvas = tk.Canvas(
            self,
            width=self.image.width,
            height=self.image.height,
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack()
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")

        self.start_x = None
        self.start_y = None
        self.rect = None

        self.canvas.bind("<ButtonPress-1>", self._start)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._finish)
        self.bind("<Escape>", lambda _event: self.destroy())

        self.info = tk.Label(
            self,
            text="Drag a rectangle around the area to search • ESC to cancel",
            font=("Segoe UI", 10),
            padx=10,
            pady=6,
        )
        self.info.pack(fill="x")

        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(0, (screen_w - self.winfo_reqwidth()) // 2)
        y = max(0, (screen_h - self.winfo_reqheight()) // 2)
        self.geometry(f"+{x}+{y}")

    def _clamp(self, x, y):
        return (
            max(0, min(self.image.width, x)),
            max(0, min(self.image.height, y)),
        )

    def _start(self, event):
        self.start_x, self.start_y = self._clamp(event.x, event.y)
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y,
            self.start_x, self.start_y,
            outline="red", width=2,
        )

    def _drag(self, event):
        if self.start_x is None:
            return
        x, y = self._clamp(event.x, event.y)
        self.canvas.coords(
            self.rect, self.start_x, self.start_y, x, y
        )

    def _finish(self, event):
        if self.start_x is None:
            return

        end_x, end_y = self._clamp(event.x, event.y)
        x1, x2 = sorted((self.start_x, end_x))
        y1, y2 = sorted((self.start_y, end_y))
        width = x2 - x1
        height = y2 - y1

        self.start_x = None

        if width < 2 or height < 2:
            return

        self.on_selected(
            DetectionRegion(
                x=int(x1),
                y=int(y1),
                width=int(width),
                height=int(height),
            )
        )
        self.destroy()


class ImageMacroApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"Image Recognition Macro v{APP_VERSION}")
        self.root.geometry("900x720")
        self.root.minsize(760, 600)

        self.template_path: str | None = None
        self.template_folder: Path | None = None
        self.current_folder: Path | None = None
        self.template_images: list[Path] = []
        self.thumbnail_refs: list[ImageTk.PhotoImage] = []
        self.detection_region: DetectionRegion | None = None

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

        template_box = ttk.LabelFrame(outer, text="1. Templates", padding=14)
        template_box.pack(fill="both", expand=True, pady=(0, 12))

        folder_bar = ttk.Frame(template_box)
        folder_bar.pack(fill="x", pady=(0, 8))

        ttk.Button(
            folder_bar, text="Select Template Folder",
            command=self.select_template_folder
        ).pack(side="left")

        self.refresh_button = ttk.Button(
            folder_bar, text="Refresh", command=self.refresh_templates,
            state="disabled"
        )
        self.refresh_button.pack(side="right")

        self.folder_label = ttk.Label(
            template_box, text="No template folder selected"
        )
        self.folder_label.pack(fill="x", pady=(0, 8))

        navigation_bar = ttk.Frame(template_box)
        navigation_bar.pack(fill="x", pady=(0, 8))

        self.back_button = ttk.Button(
            navigation_bar, text="← Back", command=self.go_back,
            state="disabled"
        )
        self.back_button.pack(side="left")

        self.home_button = ttk.Button(
            navigation_bar, text="⌂ Root", command=self.go_root,
            state="disabled"
        )
        self.home_button.pack(side="left", padx=(6, 12))

        self.breadcrumb = ttk.Label(
            navigation_bar, text="No folder selected"
        )
        self.breadcrumb.pack(side="left", fill="x", expand=True)

        self.template_count = ttk.Label(
            template_box, text="Select a folder to browse its contents."
        )
        self.template_count.pack(anchor="w", pady=(0, 8))

        gallery_frame = ttk.Frame(template_box)
        gallery_frame.pack(fill="both", expand=True)

        self.gallery_canvas = tk.Canvas(
            gallery_frame, highlightthickness=0, background="#f4f4f4"
        )
        scrollbar = ttk.Scrollbar(
            gallery_frame, orient="vertical",
            command=self.gallery_canvas.yview
        )
        self.gallery_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.gallery_canvas.pack(side="left", fill="both", expand=True)

        self.gallery_inner = ttk.Frame(self.gallery_canvas)
        self.gallery_window = self.gallery_canvas.create_window(
            (0, 0), window=self.gallery_inner, anchor="nw"
        )

        self.gallery_inner.bind(
            "<Configure>",
            lambda _event: self.gallery_canvas.configure(
                scrollregion=self.gallery_canvas.bbox("all")
            )
        )
        self.gallery_canvas.bind("<Configure>", self._resize_gallery)

        settings_box = ttk.LabelFrame(
            outer, text="2. Detection Settings", padding=14
        )
        settings_box.pack(fill="x", pady=(0, 12))

        ttk.Label(settings_box, text="Confidence").grid(
            row=0, column=0, sticky="w"
        )
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

        ttk.Label(settings_box, text="Detection Region").grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )

        region_buttons = ttk.Frame(settings_box)
        region_buttons.grid(row=2, column=1, columnspan=2, sticky="ew", padx=10, pady=(10, 0))

        ttk.Button(
            region_buttons, text="Check Screenshot & Select Region",
            command=self.select_detection_region
        ).pack(side="left")

        self.clear_region_button = ttk.Button(
            region_buttons, text="Clear Region",
            command=self.clear_detection_region,
            state="disabled"
        )
        self.clear_region_button.pack(side="left", padx=(8, 0))

        self.region_label = ttk.Label(
            settings_box, text="Full screen (no region selected)"
        )
        self.region_label.grid(
            row=3, column=1, columnspan=2, sticky="w", padx=10, pady=(6, 0)
        )

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
        status_box.pack(fill="x")

        ttk.Label(
            status_box, textvariable=self.status,
            font=("Consolas", 11), wraplength=820
        ).pack(anchor="nw")

        ttk.Label(
            outer,
            text="Tip: select a region from a fresh screenshot. Detection searches the current screen inside that region.",
            foreground="#555555"
        ).pack(anchor="w", pady=(10, 0))

        self.root.bind("<F8>", lambda _event: self.stop_loop())

    def _resize_gallery(self, event):
        self.gallery_canvas.itemconfigure(
            self.gallery_window, width=event.width
        )

    def _update_threshold_label(self, *_):
        self.threshold_value.config(text=f"{self.threshold.get():.2f}")

    def select_detection_region(self):
        try:
            screenshot = ImageGrab.grab()
        except Exception as exc:
            messagebox.showerror("Screenshot failed", str(exc))
            return

        selector = RegionSelector(
            self.root, screenshot, self._set_detection_region
        )
        selector.grab_set()
        selector.focus_force()

    def _set_detection_region(self, region: DetectionRegion):
        self.detection_region = region
        self.region_label.config(
            text=(
                f"x={region.x}, y={region.y}, "
                f"width={region.width}, height={region.height}"
            )
        )
        self.clear_region_button.config(state="normal")
        self.status.set("DETECTION REGION SET — current screen will be searched inside this area")

    def clear_detection_region(self):
        self.detection_region = None
        self.region_label.config(text="Full screen (no region selected)")
        self.clear_region_button.config(state="disabled")
        self.status.set("DETECTION REGION CLEARED — searching full screen")

    def _prepare(self) -> bool:
        if not self.template_path:
            messagebox.showwarning(
                "No template", "Select a template image from the folder first."
            )
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
                self.template_path,
                threshold=self.threshold.get(),
                region=self.detection_region,
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
                self.template_path,
                threshold=self.threshold.get(),
                region=self.detection_region,
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
            kwargs={"region": self.detection_region},
            daemon=True,
        )
        self.worker.start()

    def stop_loop(self):
        self.runner.stop()
        self.status.set("STOP REQUESTED")

    def select_template_folder(self):
        folder = filedialog.askdirectory(title="Select template root folder")
        if not folder:
            return

        self.template_folder = Path(folder)
        self.current_folder = self.template_folder
        self.folder_label.config(text=str(self.template_folder))
        self.refresh_button.config(state="normal")
        self.go_root()

    def go_root(self):
        if not self.template_folder:
            return
        self.current_folder = self.template_folder
        self.refresh_templates()

    def go_back(self):
        if not self.template_folder or not self.current_folder:
            return
        if self.current_folder == self.template_folder:
            return

        parent = self.current_folder.parent
        try:
            parent.relative_to(self.template_folder)
            self.current_folder = parent
        except ValueError:
            self.current_folder = self.template_folder

        self.refresh_templates()

    def open_subfolder(self, folder: Path):
        if not self.template_folder:
            return
        try:
            folder.relative_to(self.template_folder)
        except ValueError:
            return

        self.current_folder = folder
        self.refresh_templates()

    def refresh_templates(self):
        if not self.template_folder or not self.current_folder:
            return

        try:
            entries = list(self.current_folder.iterdir())
        except OSError as exc:
            self.status.set(f"ERROR READING FOLDER: {exc}")
            return

        subfolders = sorted(
            [
                path for path in entries
                if path.is_dir() and not path.name.startswith(".")
            ],
            key=lambda path: path.name.lower(),
        )
        self.template_images = sorted(
            [
                path for path in entries
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            ],
            key=lambda path: path.name.lower(),
        )

        for widget in self.gallery_inner.winfo_children():
            widget.destroy()

        self.thumbnail_refs.clear()

        relative = self.current_folder.relative_to(self.template_folder)
        breadcrumb = self.template_folder.name
        if str(relative) != ".":
            breadcrumb += " / " + " / ".join(relative.parts)

        self.breadcrumb.config(text=breadcrumb)
        self.back_button.config(
            state="normal" if self.current_folder != self.template_folder else "disabled"
        )
        self.home_button.config(
            state="normal" if self.current_folder != self.template_folder else "disabled"
        )

        total = len(subfolders) + len(self.template_images)
        self.template_count.config(
            text=f"{len(subfolders)} folder(s) • {len(self.template_images)} image(s) • "
                 "double-click a folder to open it, click an image to select it"
            if total else "This folder is empty."
        )

        columns = 5
        index = 0

        for folder in subfolders:
            row, column = divmod(index, columns)
            self._add_folder_card(folder, row, column)
            index += 1

        for image in self.template_images:
            row, column = divmod(index, columns)
            self._add_template_card(image, row, column)
            index += 1

        self.gallery_canvas.yview_moveto(0)

    def _add_folder_card(self, folder: Path, row: int, column: int):
        card = ttk.Frame(self.gallery_inner, padding=6, relief="ridge")
        card.grid(row=row, column=column, padx=5, pady=5, sticky="nsew")

        folder_label = tk.Label(
            card, text="📁", font=("Segoe UI Emoji", 38),
            background="#ffffff", cursor="hand2", width=8, height=2
        )
        folder_label.pack(padx=2, pady=2)

        name_label = ttk.Label(
            card, text=folder.name, anchor="center",
            wraplength=125, cursor="hand2"
        )
        name_label.pack(fill="x", pady=(3, 2))

        hint = ttk.Label(
            card, text="Double-click to open", anchor="center",
            font=("Segoe UI", 8)
        )
        hint.pack(fill="x")

        for widget in (card, folder_label, name_label, hint):
            widget.bind(
                "<Double-Button-1>",
                lambda _event, p=folder: self.open_subfolder(p)
            )

    def _add_template_card(self, path: Path, row: int, column: int):
        card = ttk.Frame(self.gallery_inner, padding=6, relief="ridge")
        card.grid(row=row, column=column, padx=5, pady=5, sticky="nsew")

        try:
            with Image.open(path) as source:
                image = source.copy()
            image.thumbnail((105, 80), Image.Resampling.LANCZOS)
            thumbnail = ImageTk.PhotoImage(image)
        except Exception:
            thumbnail = None

        if thumbnail:
            self.thumbnail_refs.append(thumbnail)
            image_label = tk.Label(
                card, image=thumbnail, background="#ffffff",
                cursor="hand2", width=105, height=80
            )
        else:
            image_label = tk.Label(
                card, text="Preview\nunavailable",
                background="#ffffff", cursor="hand2",
                width=14, height=5
            )

        image_label.pack(padx=2, pady=2)
        name_label = ttk.Label(
            card, text=path.name, anchor="center",
            wraplength=125, cursor="hand2"
        )
        name_label.pack(fill="x", pady=(3, 2))

        for widget in (card, image_label, name_label):
            widget.bind(
                "<Button-1>",
                lambda _event, p=path: self.select_template(p)
            )

    def select_template(self, path: Path):
        self.template_path = str(path)
        self.template_count.config(
            text=f"{len(self.template_images)} image(s) in current folder • Selected: {path.name}"
        )
        self.status.set(f"TEMPLATE SELECTED — {path}")

    def _prepare(self) -> bool:
        if not self.template_path:
            messagebox.showwarning(
                "No template", "Select a template image from the folder first."
            )
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
                self.template_path, threshold=self.threshold.get(),
                region=self.detection_region
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
                self.template_path, threshold=self.threshold.get(),
                region=self.detection_region
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
            kwargs={"region": self.detection_region},
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
