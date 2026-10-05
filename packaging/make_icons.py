#!/usr/bin/env python3
"""Generate platform icons (.ico / .icns / .png) from assets/logo.png into packaging/build-icons/."""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "build-icons"


def main():
    OUT.mkdir(exist_ok=True)
    logo = Image.open(ROOT / "assets" / "logo.png").convert("RGBA")

    logo.save(OUT / "chronomate.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    logo.resize((1024, 1024), Image.LANCZOS).save(OUT / "chronomate.icns")
    logo.resize((256, 256), Image.LANCZOS).save(OUT / "chronomate.png")
    print(f"Icons written to {OUT}")


if __name__ == "__main__":
    main()
