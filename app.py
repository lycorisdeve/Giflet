from __future__ import annotations

import argparse
import os
import queue
import sys
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, filedialog, messagebox, ttk
import tkinter as tk
import tkinter.font as tkfont
from tkinter.scrolledtext import ScrolledText

from PIL import Image, ImageSequence, ImageTk

from giflet_core import (
    DEFAULT_OUTPUT_DIR,
    ExtractionResult,
    extract_gif_from_file,
    extract_gif_from_url,
    extract_urls,
)


APP_TITLE = "Giflet"
REPO_URL = "https://github.com/lycorisdeve/Giflet"
TEXTS = {
    "zh": {
        "lang_button": "English",
        "ready": "就绪",
        "title": "Giflet",
        "tagline": "把抖音 AWebP 表情轻轻转成 GIF",
        "github": "GitHub",
        "source": "链接或本地图片",
        "source_hint": "像发消息一样：粘贴链接，或点按钮选择图片。",
        "placeholder": "在这里粘贴一个或多个 .awebp 链接，或在下方选择本地图片...",
        "add_images": "添加图片",
        "remove_selected": "清空图片",
        "no_files": "未选择本地图片",
        "files_selected": "{count} 张本地图片已选择",
        "output": "输出",
        "browse": "浏览",
        "extract": "提取 GIF",
        "paste": "粘贴",
        "clear": "清空",
        "open_output": "打开输出",
        "col_name": "GIF",
        "col_size": "大小",
        "col_frames": "帧数",
        "col_status": "状态",
        "done": "完成",
        "preview": "预览",
        "preview_empty": "转换后的 GIF 会显示在这里",
        "preview_hint": "输出后可直接打开文件夹继续使用",
        "run_log": "运行记录",
        "clipboard_empty": "剪贴板为空。",
        "choose_images": "选择图片",
        "added_files": "已添加 {count} 张本地图片。",
        "removed_files": "已移除 {count} 张本地图片。",
        "cleared": "已清空输入和结果列表。",
        "missing_input": "请先粘贴至少一个图片链接，或添加一张本地图片。",
        "working": "正在处理 {count} 项",
        "starting": "开始输出到 {path}",
        "downloading": "[{done}/{total}] 正在下载 {url}",
        "converting": "[{done}/{total}] 正在转换 {path}",
        "finished": "已完成 {count} 项。",
        "created": "已生成 {path}（{width}x{height}，{frames} 帧）",
        "preview_failed": "预览失败：{error}",
        "no_preview": "没有可预览的帧",
        "boot": "就绪。粘贴链接或添加本地图片，然后提取 GIF。",
    },
    "en": {
        "lang_button": "中文",
        "ready": "Ready",
        "title": "Giflet",
        "tagline": "Turn Douyin AWebP emotes into GIFs",
        "github": "GitHub",
        "source": "Links or local images",
        "source_hint": "Use it like a chat box: paste links, or choose images.",
        "placeholder": "Paste one or more .awebp links here, or choose local image files below...",
        "add_images": "Add images",
        "remove_selected": "Clear images",
        "no_files": "No local images selected",
        "files_selected": "{count} local image(s) selected",
        "output": "Output",
        "browse": "Browse",
        "extract": "Extract GIF",
        "paste": "Paste",
        "clear": "Clear",
        "open_output": "Open output",
        "col_name": "GIF",
        "col_size": "Size",
        "col_frames": "Frames",
        "col_status": "Status",
        "done": "Done",
        "preview": "Preview",
        "preview_empty": "Converted GIF preview appears here",
        "preview_hint": "Open the output folder and use the GIF anywhere",
        "run_log": "Run log",
        "clipboard_empty": "Clipboard is empty.",
        "choose_images": "Choose images",
        "added_files": "Added {count} local image(s).",
        "removed_files": "Removed {count} selected local image(s).",
        "cleared": "Cleared input and result list.",
        "missing_input": "Paste at least one image URL or add a local image.",
        "working": "Working on {count} item(s)",
        "starting": "Starting extraction into {path}",
        "downloading": "[{done}/{total}] Downloading {url}",
        "converting": "[{done}/{total}] Converting {path}",
        "finished": "Finished {count} item(s).",
        "created": "Created {path} ({width}x{height}, {frames} frames)",
        "preview_failed": "Preview failed: {error}",
        "no_preview": "No preview frames",
        "boot": "Ready. Paste links, add local images, then extract.",
    },
}
SUPPORTED_IMAGE_TYPES = (
    ("WebP / AWebP images", "*.webp *.awebp"),
    ("GIF images", "*.gif"),
    ("All image files", "*.webp *.awebp *.gif *.png *.jpg *.jpeg *.bmp"),
    ("All files", "*.*"),
)


class ExtractorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1160x740")
        self.minsize(1020, 640)

        self.output_dir = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.language = tk.StringVar(value="zh")
        self.status = tk.StringVar(value=TEXTS["zh"]["ready"])
        self.status_key = "ready"
        self.placeholder_active = True
        self.work_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.selected_files: list[Path] = []
        self.preview_frames: list[ImageTk.PhotoImage] = []
        self.preview_index = 0
        self.preview_job: str | None = None

        self._configure_style()
        self._build_layout()
        self._apply_language()
        self.after(100, self._drain_queue)

    def _text(self, key: str, **values: object) -> str:
        return TEXTS[self.language.get()][key].format(**values)

    def _configure_style(self) -> None:
        self.configure(bg="#F6F8FA")
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Segoe UI Variable", size=10)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI Variable", 10), borderwidth=0)
        style.configure("TFrame", background="#F6F8FA")
        style.configure("Header.TFrame", background="#F6F8FA")
        style.configure("Panel.TFrame", background="#FFFFFF", relief="flat")
        style.configure("Subtle.TFrame", background="#F6F8FA", relief="flat")
        style.configure("TLabel", background="#F6F8FA", foreground="#1F2328")
        style.configure("Panel.TLabel", background="#FFFFFF", foreground="#1F2328")
        style.configure("Muted.TLabel", background="#FFFFFF", foreground="#57606A")
        style.configure("Subtle.TLabel", background="#F6F8FA", foreground="#57606A")
        style.configure("Title.TLabel", background="#F6F8FA", font=("Segoe UI Variable Display", 24, "bold"), foreground="#1F2328")
        style.configure("Tagline.TLabel", background="#F6F8FA", font=("Segoe UI Variable", 10), foreground="#57606A")
        style.configure("Section.TLabel", background="#FFFFFF", font=("Segoe UI Variable", 12, "bold"), foreground="#1F2328")
        style.configure("Status.TLabel", background="#FFFFFF", foreground="#57606A", padding=(12, 6))
        style.configure("Accent.TButton", padding=(20, 11), background="#07C160", foreground="#FFFFFF", borderwidth=0)
        style.map(
            "Accent.TButton",
            background=[("active", "#06AD56"), ("pressed", "#049B4D"), ("disabled", "#A6E8C3")],
            foreground=[("disabled", "#F7FBFF")],
        )
        style.configure("TButton", padding=(13, 9), background="#F6F8FA", foreground="#24292F", bordercolor="#D0D7DE", lightcolor="#F6F8FA", darkcolor="#F6F8FA")
        style.map("TButton", background=[("active", "#EFF2F5"), ("pressed", "#EAEFF4")])
        style.configure("Ghost.TButton", padding=(13, 9), background="#FFFFFF", foreground="#57606A", bordercolor="#D0D7DE")
        style.configure("Treeview", rowheight=34, background="#FFFFFF", fieldbackground="#FFFFFF", bordercolor="#D0D7DE", lightcolor="#D0D7DE", darkcolor="#D0D7DE")
        style.configure("Treeview.Heading", font=("Segoe UI Variable", 10, "bold"), background="#F6F8FA", foreground="#57606A", bordercolor="#D0D7DE")
        style.map("Treeview", background=[("selected", "#DDF4FF")], foreground=[("selected", "#1F2328")])

    def _build_layout(self) -> None:
        header = ttk.Frame(self, style="Header.TFrame", padding=(28, 22, 28, 12))
        header.pack(fill=X)
        brand = ttk.Frame(header, style="Header.TFrame")
        brand.pack(side=LEFT)
        self.title_label = ttk.Label(brand, text="Giflet", style="Title.TLabel")
        self.title_label.pack(anchor="w")
        self.tagline_label = ttk.Label(brand, text="", style="Tagline.TLabel")
        self.tagline_label.pack(anchor="w", pady=(2, 0))
        self.github_button = tk.Button(
            header,
            text="GitHub",
            command=self._open_github,
            bg="#24292F",
            fg="#FFFFFF",
            activebackground="#32383F",
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            padx=16,
            pady=8,
            cursor="hand2",
            font=("Segoe UI Variable", 10, "bold"),
        )
        self.github_button.pack(side=RIGHT, padx=(8, 0))
        self.lang_button = ttk.Button(header, command=self._toggle_language)
        self.lang_button.pack(side=RIGHT, padx=(8, 0))
        ttk.Label(header, textvariable=self.status, style="Status.TLabel").pack(side=RIGHT)

        body = ttk.Frame(self, padding=(28, 10, 28, 28))
        body.pack(fill=BOTH, expand=True)

        left = ttk.Frame(body, style="Panel.TFrame", padding=22)
        left.pack(side=LEFT, fill=BOTH, expand=True)

        right = ttk.Frame(body, style="Panel.TFrame", padding=22)
        right.pack(side=RIGHT, fill=BOTH, expand=True, padx=(20, 0))

        self.source_label = ttk.Label(left, text="", style="Section.TLabel")
        self.source_label.pack(anchor="w")
        self.source_hint_label = ttk.Label(left, text="", style="Muted.TLabel")
        self.source_hint_label.pack(anchor="w", pady=(3, 12))
        self.url_text = ScrolledText(
            left,
            height=7,
            wrap="word",
            font=("Cascadia Mono", 10),
            borderwidth=1,
            relief="solid",
            background="#FBFBFB",
            foreground="#1F1F1F",
            insertbackground="#0067C0",
            highlightthickness=1,
            highlightcolor="#0067C0",
            highlightbackground="#DADADA",
        )
        self.url_text.pack(fill=X, pady=(8, 12))
        self.url_text.insert("1.0", self._text("placeholder"))
        self.url_text.bind("<FocusIn>", self._clear_placeholder)

        file_row = ttk.Frame(left, style="Subtle.TFrame", padding=(12, 10))
        file_row.pack(fill=X, pady=(0, 12))
        self.add_images_button = ttk.Button(file_row, command=self._choose_image_files)
        self.add_images_button.pack(side=LEFT)
        self.remove_selected_button = ttk.Button(file_row, command=self._remove_selected_files)
        self.remove_selected_button.pack(side=LEFT, padx=8)
        self.file_count = ttk.Label(file_row, text="", style="Subtle.TLabel")
        self.file_count.pack(side=LEFT, padx=8)

        path_row = ttk.Frame(left, style="Panel.TFrame")
        path_row.pack(fill=X, pady=(0, 12))
        self.output_label = ttk.Label(path_row, text="", style="Panel.TLabel")
        self.output_label.pack(side=LEFT)
        ttk.Entry(path_row, textvariable=self.output_dir).pack(side=LEFT, fill=X, expand=True, padx=8)
        self.browse_button = ttk.Button(path_row, style="Ghost.TButton", command=self._choose_output_dir)
        self.browse_button.pack(side=RIGHT)

        actions = ttk.Frame(left, style="Panel.TFrame")
        actions.pack(fill=X, pady=(0, 12))
        self.convert_button = ttk.Button(actions, style="Accent.TButton", command=self._start_extraction)
        self.convert_button.pack(side=LEFT)
        self.paste_button = ttk.Button(actions, style="Ghost.TButton", command=self._paste_clipboard)
        self.paste_button.pack(side=LEFT, padx=8)
        self.clear_button = ttk.Button(actions, style="Ghost.TButton", command=self._clear_inputs)
        self.clear_button.pack(side=LEFT)
        self.open_output_button = ttk.Button(actions, style="Ghost.TButton", command=self._open_output_dir)
        self.open_output_button.pack(side=RIGHT)

        columns = ("name", "size", "frames", "status")
        self.results = ttk.Treeview(left, columns=columns, show="headings", height=10)
        self.results.heading("name", text="")
        self.results.heading("size", text="")
        self.results.heading("frames", text="")
        self.results.heading("status", text="")
        self.results.column("name", width=260)
        self.results.column("size", width=90, anchor="e")
        self.results.column("frames", width=80, anchor="center")
        self.results.column("status", width=120)
        self.results.pack(fill=BOTH, expand=True)
        self.results.bind("<<TreeviewSelect>>", self._preview_selected)

        self.preview_title = ttk.Label(right, text="", style="Section.TLabel")
        self.preview_title.pack(anchor="w")
        self.preview_hint_label = ttk.Label(right, text="", style="Muted.TLabel")
        self.preview_hint_label.pack(anchor="w", pady=(3, 12))
        preview_box = ttk.Frame(right, style="Panel.TFrame")
        preview_box.pack(fill=BOTH, expand=True, pady=(8, 12))
        self.preview_label = ttk.Label(preview_box, text="", style="Muted.TLabel", anchor="center")
        self.preview_label.pack(fill=BOTH, expand=True)

        self.log_title = ttk.Label(right, text="", style="Section.TLabel")
        self.log_title.pack(anchor="w")
        self.log = ScrolledText(
            right,
            height=10,
            wrap="word",
            font=("Cascadia Mono", 9),
            borderwidth=1,
            relief="solid",
            background="#202020",
            foreground="#EDEDED",
            insertbackground="#FFFFFF",
            highlightthickness=1,
            highlightcolor="#8AB4F8",
            highlightbackground="#DADADA",
        )
        self.log.pack(fill=X, pady=(8, 0))
        self._log(self._text("boot"))

    def _apply_language(self) -> None:
        self.lang_button.configure(text=self._text("lang_button"))
        self.title_label.configure(text=self._text("title"))
        self.tagline_label.configure(text=self._text("tagline"))
        self.github_button.configure(text=self._text("github"))
        self.source_label.configure(text=self._text("source"))
        self.source_hint_label.configure(text=self._text("source_hint"))
        self.add_images_button.configure(text=self._text("add_images"))
        self.remove_selected_button.configure(text=self._text("remove_selected"))
        self.output_label.configure(text=self._text("output"))
        self.browse_button.configure(text=self._text("browse"))
        self.convert_button.configure(text=self._text("extract"))
        self.paste_button.configure(text=self._text("paste"))
        self.clear_button.configure(text=self._text("clear"))
        self.open_output_button.configure(text=self._text("open_output"))
        self.results.heading("name", text=self._text("col_name"))
        self.results.heading("size", text=self._text("col_size"))
        self.results.heading("frames", text=self._text("col_frames"))
        self.results.heading("status", text=self._text("col_status"))
        self.preview_title.configure(text=self._text("preview"))
        self.preview_hint_label.configure(text=self._text("preview_hint"))
        self.log_title.configure(text=self._text("run_log"))
        if self.placeholder_active:
            self.url_text.delete("1.0", END)
            self.url_text.insert("1.0", self._text("placeholder"))
        if not self.preview_frames:
            self.preview_label.configure(text=self._text("preview_empty"))
        self._set_status(self.status_key)
        self._update_file_count()

    def _toggle_language(self) -> None:
        self.language.set("en" if self.language.get() == "zh" else "zh")
        self._apply_language()

    def _open_github(self) -> None:
        webbrowser.open(REPO_URL)

    def _set_status(self, key: str, **values: object) -> None:
        self.status_key = key
        self.status.set(self._text(key, **values))

    def _clear_placeholder(self, _event: object) -> None:
        if self.placeholder_active:
            self.url_text.delete("1.0", END)
            self.placeholder_active = False

    def _choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_dir.get() or str(DEFAULT_OUTPUT_DIR))
        if selected:
            self.output_dir.set(selected)

    def _paste_clipboard(self) -> None:
        try:
            text = self.clipboard_get()
        except tk.TclError:
            messagebox.showinfo(APP_TITLE, self._text("clipboard_empty"))
            return
        self._clear_placeholder(None)
        self.url_text.insert(END, ("\n" if self.url_text.get("1.0", END).strip() else "") + text)

    def _choose_image_files(self) -> None:
        selected = filedialog.askopenfilenames(title=self._text("choose_images"), filetypes=SUPPORTED_IMAGE_TYPES)
        added = 0
        for item in selected:
            path = Path(item)
            if path not in self.selected_files:
                self.selected_files.append(path)
                added += 1
        self._update_file_count()
        if added:
            self._log(self._text("added_files", count=added))

    def _remove_selected_files(self) -> None:
        if self.selected_files:
            removed = len(self.selected_files)
            self.selected_files.clear()
            self._update_file_count()
            self._log(self._text("removed_files", count=removed))

    def _update_file_count(self) -> None:
        count = len(self.selected_files)
        if count == 0:
            self.file_count.configure(text=self._text("no_files"))
        else:
            self.file_count.configure(text=self._text("files_selected", count=count))

    def _clear_inputs(self) -> None:
        self.url_text.delete("1.0", END)
        self.placeholder_active = False
        self.selected_files.clear()
        self._update_file_count()
        for item in self.results.get_children():
            self.results.delete(item)
        self._stop_preview()
        self.preview_label.configure(image="", text=self._text("preview_empty"))
        self._log(self._text("cleared"))

    def _start_extraction(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        urls = extract_urls(self.url_text.get("1.0", END))
        files = list(self.selected_files)
        if not urls and not files:
            messagebox.showwarning(APP_TITLE, self._text("missing_input"))
            return
        out_dir = Path(self.output_dir.get()).expanduser()
        self.convert_button.state(["disabled"])
        total = len(urls) + len(files)
        self._set_status("working", count=total)
        self._log(self._text("starting", path=out_dir))
        texts = TEXTS[self.language.get()]
        self.worker = threading.Thread(target=self._extract_worker, args=(urls, files, out_dir, texts), daemon=True)
        self.worker.start()

    def _extract_worker(self, urls: list[str], files: list[Path], out_dir: Path, texts: dict[str, str]) -> None:
        total = len(urls) + len(files)
        completed = 0
        for index, url in enumerate(urls, start=1):
            completed += 1
            self.work_queue.put(("log", texts["downloading"].format(done=completed, total=total, url=url)))
            try:
                result = extract_gif_from_url(url, out_dir, index)
            except Exception as exc:
                self.work_queue.put(("error", f"[{completed}/{total}] {exc}"))
            else:
                self.work_queue.put(("result", result))
        for offset, path in enumerate(files, start=1):
            completed += 1
            self.work_queue.put(("log", texts["converting"].format(done=completed, total=total, path=path)))
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
                    self._set_status("ready")
                    self._log(self._text("finished", count=payload))
        except queue.Empty:
            pass
        self.after(100, self._drain_queue)

    def _add_result(self, result: ExtractionResult) -> None:
        size = _format_bytes(result.gif_bytes)
        label = result.gif_path.name
        item = self.results.insert(
            "",
            END,
            values=(label, size, f"{result.frames}", self._text("done")),
            tags=(str(result.gif_path),),
        )
        self.results.selection_set(item)
        self.results.focus(item)
        self._log(self._text("created", path=result.gif_path, width=result.width, height=result.height, frames=result.frames))
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
            self.preview_label.configure(text=self._text("preview_failed", error=exc), image="")
            return
        if not frames:
            self.preview_label.configure(text=self._text("no_preview"), image="")
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
