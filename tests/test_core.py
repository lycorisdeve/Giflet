import tempfile
import unittest
from pathlib import Path

from PIL import Image

from giflet_core import extract_gif_from_file, extract_urls


class GifletCoreTests(unittest.TestCase):
    def test_extract_urls_deduplicates_preserving_order(self):
        text = "one https://example.test/a.awebp?x=1 two https://example.test/a.awebp?x=1 https://example.test/b.webp"

        self.assertEqual(
            extract_urls(text),
            ["https://example.test/a.awebp?x=1", "https://example.test/b.webp"],
        )

    def test_extract_gif_from_local_animated_webp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sample.webp"
            output = root / "out"
            frame_a = Image.new("RGBA", (12, 10), (255, 0, 0, 255))
            frame_b = Image.new("RGBA", (12, 10), (0, 255, 0, 255))
            frame_a.save(source, save_all=True, append_images=[frame_b], duration=[80, 120], loop=0, format="WEBP")

            result = extract_gif_from_file(source, output)

            self.assertTrue(result.gif_path.is_file())
            self.assertEqual((result.width, result.height), (12, 10))
            self.assertGreaterEqual(result.frames, 1)


if __name__ == "__main__":
    unittest.main()
