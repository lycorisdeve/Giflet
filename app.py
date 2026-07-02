from __future__ import annotations

import argparse
import shutil
import os
import queue
import re
import sys
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, filedialog, messagebox, ttk
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from PIL import Image, ImageSequence, ImageTk


APP_TITLE = "Giflet"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "exports"
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
SUPPORTED_IMAGE_TYPES = (
    ("WebP / AWebP images", "*.webp *.awebp"),
    ("GIF images", "*.gif"),
    ("All image files", "*.webp *.awebp *.gif *.png *.jpg *.jpeg *.bmp"),
    ("All files", "*.*"),
)


@dataclass(frozen=True)
class ExtractionResult:
    source: str
    original_path: Path
    gif_path: Path
    width: int
    height: int
    frames: int
    gif_bytes: int


def extract_urls(text: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for match in URL_RE.finditer(text):
        url = match.group(0).strip()
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _safe_stem_from_url(url: str, index: int) -> str:
    parsed = urllib.parse.urlparse(url)
    name = Path(parsed.path).name or f"emoticon-{index}"
    name = name.split("~", 1)[0]
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    if not name:
        name = f"emoticon-{index}"
    if name.lower().endswith((".awebp", ".webp", ".gif")):
        name = Path(name).stem
    return name[:64]


def _safe_stem_from_name(name: str, fallback: str) -> str:
    stem = Path(name).stem or fallback
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-")
    return (stem or fallback)[:64]


def _unique_path(directory: Path, stem: str, suffix: str) -> Path:
    candidate = directory / f"{stem}{suffix}"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def _normalized_original_suffix(source: Path) -> str:
    suffix = source.suffix.lower()
    return suffix if suffix in {".awebp", ".webp", ".gif", ".png", ".jpg", ".jpeg", ".bmp"} else ".img"


def download_file(url: str, destination: Path) -> int:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 AWebP-GIF-Extractor/1.0",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read()
    destination.write_bytes(data)
    return len(data)


def convert_animated_webp_to_gif(source: Path, destination: Path) -> tuple[int, int, int]:
    image = Image.open(source)
    frames: list[Image.Image] = []
    durations: list[int] = []

    for frame in ImageSequence.Iterator(image):
        frames.append(frame.convert("RGBA").copy())
        durations.append(int(frame.info.get("duration", image.info.get("duration", 100)) or 100))

    if not frames:
        raise ValueError("No image frames were found.")

    frames[0].save(
        destination,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        disposal=2,
        optimize=False,
    )
    width, height = frames[0].size
    return width, height, len(frames)


def extract_gif_from_file(source: Path, output_dir: Path, index: int = 1) -> ExtractionResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Image file does not exist: {source}")

    stem = _safe_stem_from_name(source.name, f"image-{index}")
    original_path = _unique_path(output_dir, stem, _normalized_original_suffix(source))
    gif_path = _unique_path(output_dir, stem, ".gif")
    shutil.copy2(source, original_path)
    width, height, frames = convert_animated_webp_to_gif(original_path, gif_path)

    return ExtractionResult(
        source=str(source),
        original_path=original_path,
        gif_path=gif_path,
        width=width,
        height=height,
        frames=frames,
        gif_bytes=gif_path.stat().st_size,
    )


def extract_gif_from_bytes(data: bytes, filename: str, output_dir: Path, index: int = 1) -> ExtractionResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem_from_name(filename, f"upload-{index}")
    suffix = Path(filename).suffix.lower() or ".awebp"
    if suffix not in {".awebp", ".webp", ".gif", ".png", ".jpg", ".jpeg", ".bmp"}:
        suffix = ".img"
    original_path = _unique_path(output_dir, stem, suffix)
    gif_path = _unique_path(output_dir, stem, ".gif")
    original_path.write_bytes(data)
    width, height, frames = convert_animated_webp_to_gif(original_path, gif_path)

    return ExtractionResult(
        source=filename,
        original_path=original_path,
        gif_path=gif_path,
        width=width,
        height=height,
        frames=frames,
        gif_bytes=gif_path.stat().st_size,
    )


def extract_gif_from_url(url: str, output_dir: Path, index: int = 1) -> ExtractionResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem_from_url(url, index)
    original_path = _unique_path(output_dir, stem, ".awebp")
    gif_path = _unique_path(output_dir, stem, ".gif")

    download_file(url, original_path)
    width, height, frames = convert_animated_webp_to_gif(original_path, gif_path)

    return ExtractionResult(
        source=url,
        original_path=original_path,
        gif_path=gif_path,
        width=width,
        height=height,
        frames=frames,
        gif_bytes=gif_path.stat().st_size,
    )


class ExtractorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1040x680")
        self.minsize(940, 600)

        self.output_dir = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.status = tk.StringVar(value="Ready")
        self.work_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.selected_files: list[Path] = []
        self.preview_frames: list[ImageTk.PhotoImage] = []
        self.preview_index = 0
        self.preview_job: str | None = None

        self._configure_style()
        self._build_layout()
        self.after(100, self._drain_queue)

    def _configure_style(self) -> None:
        self.configure(bg="#F7F3EA")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background="#F7F3EA")
        style.configure("Panel.TFrame", background="#FFFDF8", relief="flat")
        style.configure("TLabel", background="#F7F3EA", foreground="#1F2A2E")
        style.configure("Panel.TLabel", background="#FFFDF8", foreground="#1F2A2E")
        style.configure("Muted.TLabel", background="#FFFDF8", foreground="#617073")
        style.configure("Title.TLabel", background="#F7F3EA", font=("Segoe UI Semibold", 18), foreground="#142326")
        style.configure("Accent.TButton", padding=(16, 10), background="#0E7C7B", foreground="#FFFFFF")
        style.map("Accent.TButton", background=[("active", "#0B6463"), ("disabled", "#9CB8B8")])
        style.configure("TButton", padding=(12, 8), background="#E4E0D7")
        style.configure("Treeview", rowheight=28, background="#FFFDF8", fieldbackground="#FFFDF8")
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10))

    def _build_layout(self) -> None:
        header = ttk.Frame(self, padding=(22, 18, 22, 8))
        header.pack(fill=X)
        ttk.Label(header, text="Giflet", style="Title.TLabel").pack(side=LEFT)
        ttk.Label(header, textvariable=self.status).pack(side=RIGHT)

        body = ttk.Frame(self, padding=(22, 10, 22, 20))
        body.pack(fill=BOTH, expand=True)

        left = ttk.Frame(body, style="Panel.TFrame", padding=16)
        left.pack(side=LEFT, fill=BOTH, expand=True)

        right = ttk.Frame(body, style="Panel.TFrame", padding=16)
        right.pack(side=RIGHT, fill=BOTH, expand=True, padx=(16, 0))

        ttk.Label(left, text="Links or local images", style="Panel.TLabel", font=("Segoe UI Semibold", 11)).pack(anchor="w")
        self.url_text = ScrolledText(left, height=8, wrap="word", font=("Consolas", 10), borderwidth=1, relief="solid")
        self.url_text.pack(fill=X, pady=(8, 12))
        self.url_text.insert("1.0", "Paste one or more .awebp links here, or choose local image files below...")
        self.url_text.bind("<FocusIn>", self._clear_placeholder)

        file_row = ttk.Frame(left, style="Panel.TFrame")
        file_row.pack(fill=X, pady=(0, 12))
        ttk.Button(file_row, text="Add images", command=self._choose_image_files).pack(side=LEFT)
        ttk.Button(file_row, text="Remove selected", command=self._remove_selected_files).pack(side=LEFT, padx=8)
        self.file_count = ttk.Label(file_row, text="No local images selected", style="Muted.TLabel")
        self.file_count.pack(side=LEFT, padx=8)

        path_row = ttk.Frame(left, style="Panel.TFrame")
        path_row.pack(fill=X, pady=(0, 12))
        ttk.Label(path_row, text="Output", style="Panel.TLabel").pack(side=LEFT)
        ttk.Entry(path_row, textvariable=self.output_dir).pack(side=LEFT, fill=X, expand=True, padx=8)
        ttk.Button(path_row, text="Browse", command=self._choose_output_dir).pack(side=RIGHT)

        actions = ttk.Frame(left, style="Panel.TFrame")
        actions.pack(fill=X, pady=(0, 12))
        self.convert_button = ttk.Button(actions, text="Extract GIF", style="Accent.TButton", command=self._start_extraction)
        self.convert_button.pack(side=LEFT)
        ttk.Button(actions, text="Paste", command=self._paste_clipboard).pack(side=LEFT, padx=8)
        ttk.Button(actions, text="Clear", command=self._clear_inputs).pack(side=LEFT)
        ttk.Button(actions, text="Open output", command=self._open_output_dir).pack(side=RIGHT)

        columns = ("name", "size", "frames", "status")
        self.results = ttk.Treeview(left, columns=columns, show="headings", height=10)
        self.results.heading("name", text="GIF")
        self.results.heading("size", text="Size")
        self.results.heading("frames", text="Frames")
        self.results.heading("status", text="Status")
        self.results.column("name", width=260)
        self.results.column("size", width=90, anchor="e")
        self.results.column("frames", width=80, anchor="center")
        self.results.column("status", width=120)
        self.results.pack(fill=BOTH, expand=True)
        self.results.bind("<<TreeviewSelect>>", self._preview_selected)

        ttk.Label(right, text="Preview", style="Panel.TLabel", font=("Segoe UI Semibold", 11)).pack(anchor="w")
        preview_box = ttk.Frame(right, style="Panel.TFrame")
        preview_box.pack(fill=BOTH, expand=True, pady=(8, 12))
        self.preview_label = ttk.Label(preview_box, text="Converted GIF preview appears here", style="Muted.TLabel", anchor="center")
        self.preview_label.pack(fill=BOTH, expand=True)

        ttk.Label(right, text="Run log", style="Panel.TLabel", font=("Segoe UI Semibold", 11)).pack(anchor="w")
        self.log = ScrolledText(right, height=10, wrap="word", font=("Consolas", 9), borderwidth=1, relief="solid")
        self.log.pack(fill=X, pady=(8, 0))
        self._log("Ready. Paste links, add local images, then extract.")

    def _clear_placeholder(self, _event: object) -> None:
        if self.url_text.get("1.0", END).strip() == "Paste one or more .awebp links here, or choose local image files below...":
            self.url_text.delete("1.0", END)

    def _choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_dir.get() or str(DEFAULT_OUTPUT_DIR))
        if selected:
            self.output_dir.set(selected)

    def _paste_clipboard(self) -> None:
        try:
            text = self.clipboard_get()
        except tk.TclError:
            messagebox.showinfo(APP_TITLE, "Clipboard is empty.")
            return
        self._clear_placeholder(None)
        self.url_text.insert(END, ("\n" if self.url_text.get("1.0", END).strip() else "") + text)

    def _choose_image_files(self) -> None:
        selected = filedialog.askopenfilenames(title="Choose images", filetypes=SUPPORTED_IMAGE_TYPES)
        added = 0
        for item in selected:
            path = Path(item)
            if path not in self.selected_files:
                self.selected_files.append(path)
                added += 1
        self._update_file_count()
        if added:
            self._log(f"Added {added} local image(s).")

    def _remove_selected_files(self) -> None:
        if self.selected_files:
            removed = len(self.selected_files)
            self.selected_files.clear()
            self._update_file_count()
            self._log(f"Removed {removed} selected local image(s).")

    def _update_file_count(self) -> None:
        count = len(self.selected_files)
        if count == 0:
            self.file_count.configure(text="No local images selected")
        else:
            self.file_count.configure(text=f"{count} local image(s) selected")

    def _clear_inputs(self) -> None:
        self.url_text.delete("1.0", END)
        self.selected_files.clear()
        self._update_file_count()
        for item in self.results.get_children():
            self.results.delete(item)
        self._stop_preview()
        self.preview_label.configure(image="", text="Converted GIF preview appears here")
        self._log("Cleared input and result list.")

    def _start_extraction(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        urls = extract_urls(self.url_text.get("1.0", END))
        files = list(self.selected_files)
        if not urls and not files:
            messagebox.showwarning(APP_TITLE, "Paste at least one image URL or add a local image.")
            return
        out_dir = Path(self.output_dir.get()).expanduser()
        self.convert_button.state(["disabled"])
        total = len(urls) + len(files)
        self.status.set(f"Working on {total} item(s)")
        self._log(f"Starting extraction into {out_dir}")
        self.worker = threading.Thread(target=self._extract_worker, args=(urls, files, out_dir), daemon=True)
        self.worker.start()

    def _extract_worker(self, urls: list[str], files: list[Path], out_dir: Path) -> None:
        total = len(urls) + len(files)
        completed = 0
        for index, url in enumerate(urls, start=1):
            completed += 1
            self.work_queue.put(("log", f"[{completed}/{total}] Downloading {url}"))
            try:
                result = extract_gif_from_url(url, out_dir, index)
            except Exception as exc:
                self.work_queue.put(("error", f"[{completed}/{total}] {exc}"))
            else:
                self.work_queue.put(("result", result))
        for offset, path in enumerate(files, start=1):
            completed += 1
            self.work_queue.put(("log", f"[{completed}/{total}] Converting {path}"))
            try:
                result = extract_gif_from_file(path, out_dir, len(urls) + offset)
            except Exception as exc:
                self.work_queue.put(("error", f"[{completed}/{total}] {exc}"))
            else:
                self.work_queue.put(("result", result))
        self.work_queue.put(("done", total))

    def _drain_queue(self) -> None:
        try:
            while True:
                kind, payload = self.work_queue.get_nowait()
                if kind == "log":
                    self._log(str(payload))
                elif kind == "error":
                    self._log("ERROR " + str(payload))
                elif kind == "result":
                    self._add_result(payload)  # type: ignore[arg-type]
                elif kind == "done":
                    self.convert_button.state(["!disabled"])
                    self.status.set("Ready")
                    self._log(f"Finished {payload} item(s).")
        except queue.Empty:
            pass
        self.after(100, self._drain_queue)

    def _add_result(self, result: ExtractionResult) -> None:
        size = _format_bytes(result.gif_bytes)
        label = result.gif_path.name
        item = self.results.insert(
            "",
            END,
            values=(label, size, f"{result.frames}", "Done"),
            tags=(str(result.gif_path),),
        )
        self.results.selection_set(item)
        self.results.focus(item)
        self._log(f"Created {result.gif_path} ({result.width}x{result.height}, {result.frames} frames)")
        self._load_preview(result.gif_path)

    def _preview_selected(self, _event: object) -> None:
        selected = self.results.selection()
        if not selected:
            return
        tags = self.results.item(selected[0], "tags")
        if tags:
            self._load_preview(Path(tags[0]))

    def _load_preview(self, path: Path) -> None:
        self._stop_preview()
        try:
            image = Image.open(path)
            max_w, max_h = 380, 360
            frames = []
            for frame in ImageSequence.Iterator(image):
                preview = frame.convert("RGBA").copy()
                preview.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                frames.append(ImageTk.PhotoImage(preview))
        except Exception as exc:
            self.preview_label.configure(text=f"Preview failed: {exc}", image="")
            return
        if not frames:
            self.preview_label.configure(text="No preview frames", image="")
            return
        self.preview_frames = frames
        self.preview_index = 0
        self._animate_preview()

    def _animate_preview(self) -> None:
        if not self.preview_frames:
            return
        frame = self.preview_frames[self.preview_index]
        self.preview_label.configure(image=frame, text="")
        self.preview_index = (self.preview_index + 1) % len(self.preview_frames)
        self.preview_job = self.after(100, self._animate_preview)

    def _stop_preview(self) -> None:
        if self.preview_job is not None:
            self.after_cancel(self.preview_job)
            self.preview_job = None
        self.preview_frames = []

    def _open_output_dir(self) -> None:
        path = Path(self.output_dir.get()).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)  # type: ignore[attr-defined]

    def _log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log.insert(END, f"{timestamp}  {message}\n")
        self.log.see(END)


def _format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def run_cli(args: argparse.Namespace) -> int:
    output_dir = Path(args.output).expanduser()
    urls = args.url or []
    images = [Path(item) for item in (args.image or [])]
    if args.file:
        urls.extend(extract_urls(Path(args.file).read_text(encoding="utf-8")))
    if not urls and not images:
        print("No URL or image file provided.", file=sys.stderr)
        return 2
    for index, url in enumerate(urls, start=1):
        result = extract_gif_from_url(url, output_dir, index)
        print(f"{result.gif_path} ({result.width}x{result.height}, {result.frames} frames)")
    for offset, image in enumerate(images, start=1):
        result = extract_gif_from_file(image, output_dir, len(urls) + offset)
        print(f"{result.gif_path} ({result.width}x{result.height}, {result.frames} frames)")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract GIF files from animated .awebp URLs or local image files.")
    parser.add_argument("--url", action="append", help="Animated .awebp URL. Repeat for batch mode.")
    parser.add_argument("--image", action="append", help="Local image file. Repeat for batch mode.")
    parser.add_argument("--file", help="Text file containing URLs.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_DIR), help="Output directory.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.url or args.file or args.image:
        return run_cli(args)
    app = ExtractorApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
