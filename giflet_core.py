from __future__ import annotations

import re
import shutil
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageSequence


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "exports"
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


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


def safe_stem_from_url(url: str, index: int) -> str:
    parsed = urllib.parse.urlparse(url)
    name = Path(parsed.path).name or f"emoticon-{index}"
    name = name.split("~", 1)[0]
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    if not name:
        name = f"emoticon-{index}"
    if name.lower().endswith((".awebp", ".webp", ".gif")):
        name = Path(name).stem
    return name[:64]


def safe_stem_from_name(name: str, fallback: str) -> str:
    stem = Path(name).stem or fallback
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-")
    return (stem or fallback)[:64]


def unique_path(directory: Path, stem: str, suffix: str) -> Path:
    candidate = directory / f"{stem}{suffix}"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def normalized_original_suffix(source: Path) -> str:
    suffix = source.suffix.lower()
    return suffix if suffix in {".awebp", ".webp", ".gif", ".png", ".jpg", ".jpeg", ".bmp"} else ".img"


def download_file(url: str, destination: Path) -> int:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 Giflet/1.0",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read()
    destination.write_bytes(data)
    return len(data)


def convert_image_to_gif(source: Path, destination: Path) -> tuple[int, int, int]:
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

    stem = safe_stem_from_name(source.name, f"image-{index}")
    original_path = unique_path(output_dir, stem, normalized_original_suffix(source))
    gif_path = unique_path(output_dir, stem, ".gif")
    shutil.copy2(source, original_path)
    width, height, frames = convert_image_to_gif(original_path, gif_path)

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
    stem = safe_stem_from_name(filename, f"upload-{index}")
    suffix = Path(filename).suffix.lower() or ".awebp"
    if suffix not in {".awebp", ".webp", ".gif", ".png", ".jpg", ".jpeg", ".bmp"}:
        suffix = ".img"
    original_path = unique_path(output_dir, stem, suffix)
    gif_path = unique_path(output_dir, stem, ".gif")
    original_path.write_bytes(data)
    width, height, frames = convert_image_to_gif(original_path, gif_path)

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
    stem = safe_stem_from_url(url, index)
    original_path = unique_path(output_dir, stem, ".awebp")
    gif_path = unique_path(output_dir, stem, ".gif")

    download_file(url, original_path)
    width, height, frames = convert_image_to_gif(original_path, gif_path)

    return ExtractionResult(
        source=url,
        original_path=original_path,
        gif_path=gif_path,
        width=width,
        height=height,
        frames=frames,
        gif_bytes=gif_path.stat().st_size,
    )
