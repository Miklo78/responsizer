#!/usr/bin/env python3
"""
RESPONSIZER — Batch image resizer for srcset workflows.

Generates multiple image sizes for responsive <picture> / srcset usage.
Cross-platform: macOS, Windows, Linux.

Usage:
    responsizer 840,420,330
    responsizer 840,420 --also-webp 85 --also-avif 75
    responsizer 840,420 --format webp:85
    responsizer 840,420 --source ./imgs --output ./out
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Check for Pillow
# ---------------------------------------------------------------------------
try:
    from PIL import Image
except ImportError:
    print()
    print("  X Error: Pillow library is not installed.")
    print()
    print("  Install it with:")
    print("    pip install Pillow")
    print()
    print("  (If you don't have pip, install Python first — see README.)")
    print()
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VERSION = "0.1.0"
SUPPORTED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".avif",
    ".gif", ".tiff", ".tif", ".bmp",
}

FORMAT_MAP = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".webp": "WEBP",
    ".avif": "AVIF",
    ".gif": "GIF",
    ".tiff": "TIFF",
    ".tif": "TIFF",
    ".bmp": "BMP",
}

EXTENSION_MAP = {
    "png": ".png",
    "jpg": ".jpg",
    "jpeg": ".jpg",
    "webp": ".webp",
    "avif": ".avif",
    "gif": ".gif",
    "tiff": ".tiff",
    "bmp": ".bmp",
}


# ---------------------------------------------------------------------------
# Terminal colors
# ---------------------------------------------------------------------------
class C:
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    RED = "\033[0;31m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    NC = "\033[0m"

    @staticmethod
    def disable():
        C.GREEN = C.YELLOW = C.BLUE = C.RED = C.DIM = C.BOLD = C.NC = ""


if sys.platform == "win32" and "WT_SESSION" not in os.environ:
    try:
        os.system("")
    except Exception:
        C.disable()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_banner():
    print()
    print(f"{C.BLUE}{'=' * 60}{C.NC}")
    print(f"{C.BLUE}  RESPONSIZER {VERSION} — srcset image batch resizer{C.NC}")
    print(f"{C.BLUE}{'=' * 60}{C.NC}")
    print()


def parse_format_spec(spec):
    """Parse format spec like 'webp:85' or 'png' into (format, quality)."""
    if ":" in spec:
        fmt, q = spec.split(":", 1)
        return fmt.strip().lower(), int(q.strip())
    return spec.strip().lower(), None


def strip_size_label(name):
    """
    Remove existing size label from filename.
    Detects patterns like -840w, -w840, -600h, -h600 at end of name.
    """
    patterns = [
        r'-(\d+)[wWhH]$',     # -840w, -600h
        r'-[wWhH](\d+)$',     # -w840, -h600
    ]
    for pattern in patterns:
        name = re.sub(pattern, '', name)
    return name


def build_output_name(base_name, size, by, label_pos, ext):
    """Build output filename like 'hero-840w.png' or 'hero-w840.png'."""
    label_char = "w" if by == "width" else "h"
    clean_name = strip_size_label(base_name)

    if label_pos == "after":
        return f"{clean_name}-{size}{label_char}{ext}"
    else:
        return f"{clean_name}-{label_char}{size}{ext}"


def get_save_kwargs(fmt, quality, keep_exif, exif_data=None):
    """Build kwargs for Pillow Image.save()."""
    kwargs = {}
    if fmt == "JPEG":
        kwargs["quality"] = quality or 90
        kwargs["optimize"] = True
        if keep_exif and exif_data:
            kwargs["exif"] = exif_data
    elif fmt == "WEBP":
        kwargs["quality"] = quality or 85
        kwargs["method"] = 4
    elif fmt == "AVIF":
        kwargs["quality"] = quality or 75
    elif fmt == "PNG":
        kwargs["optimize"] = True
    return kwargs


def has_cwebp():
    return shutil.which("cwebp") is not None


def has_avifenc():
    return shutil.which("avifenc") is not None


def convert_with_cwebp(input_path, output_path, quality):
    """Convert to WebP using cwebp (better compression than Pillow)."""
    try:
        cmd = ["cwebp", "-q", str(quality), "-m", "6",
               input_path, "-o", output_path]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def convert_with_avifenc(input_path, output_path, quality):
    """Convert to AVIF using avifenc (better compression than Pillow)."""
    try:
        cmd = ["avifenc", "--min", "0", "--max", "63",
               "-a", f"cq-level={100 - quality}",
               "-a", "end-usage=q", "--speed", "6",
               input_path, output_path]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def resize_image(img, size, by, allow_upscale=False):
    """
    Resize image by width or height, maintaining aspect ratio.
    Returns None if upscale would be needed and not allowed.
    """
    orig_w, orig_h = img.size

    if by == "width":
        if orig_w < size and not allow_upscale:
            return None
        ratio = size / orig_w
        new_w = size
        new_h = round(orig_h * ratio)
    else:
        if orig_h < size and not allow_upscale:
            return None
        ratio = size / orig_h
        new_h = size
        new_w = round(orig_w * ratio)

    return img.resize((new_w, new_h), Image.LANCZOS)


def find_source_images(source_dir):
    """Find all supported image files in source directory."""
    images = []
    for f in sorted(source_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
            images.append(f)
    return images


def load_preset(preset_name, config_path=None):
    """Load widths from a preset in .responsizer.json config file."""
    search_paths = []
    if config_path:
        search_paths.append(config_path)
    search_paths.extend([
        Path.cwd() / ".responsizer.json",
        Path.home() / ".responsizer.json",
    ])

    for p in search_paths:
        if p.exists():
            try:
                with open(p) as f:
                    config = json.load(f)
                presets = config.get("presets", {})
                if preset_name in presets:
                    return presets[preset_name]
            except (json.JSONDecodeError, KeyError):
                pass
    return None


def format_size(bytes_size):
    """Format file size for human display."""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    else:
        return f"{bytes_size / (1024 * 1024):.1f} MB"


def prepare_for_save(img, target_format):
    """Prepare image for saving — handle RGBA to JPEG, palette mode, etc."""
    result = img

    # Convert palette mode
    if result.mode == "P":
        result = result.convert("RGBA")

    # JPEG doesn't support alpha — flatten to white background
    if target_format == "JPEG" and result.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", result.size, (255, 255, 255))
        bg.paste(result, mask=result.split()[-1])
        result = bg
    elif target_format == "JPEG" and result.mode != "RGB":
        result = result.convert("RGB")

    return result


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process(args):
    print_banner()

    # --- Resolve sizes ---
    sizes = []
    if args.preset:
        preset_sizes = load_preset(args.preset, args.config)
        if preset_sizes is None:
            print(f"{C.RED}  X Preset '{args.preset}' not found.{C.NC}")
            print(f"    Create a .responsizer.json file with:")
            print(f'    {{"presets": {{"{args.preset}": [840, 420, 330]}}}}')
            sys.exit(1)
        sizes = preset_sizes
        print(f"  {C.DIM}Preset: {args.preset}{C.NC}")

    if args.sizes:
        for s in args.sizes.split(","):
            s = s.strip()
            if s.isdigit():
                sizes.append(int(s))
            else:
                print(f"{C.RED}  X Invalid size: '{s}' — enter a whole number in pixels.{C.NC}")
                sys.exit(1)

    if not sizes:
        print(f"{C.RED}  X No sizes specified.{C.NC}")
        print(f"    Example: responsizer 840,420,330")
        sys.exit(1)

    sizes = sorted(set(sizes), reverse=True)

    # --- Resolve paths ---
    source_dir = Path(args.source).resolve()
    output_dir = Path(args.output).resolve()

    if not source_dir.exists():
        print(f"{C.RED}  X Source directory not found: {source_dir}{C.NC}")
        sys.exit(1)

    # --- Find images ---
    images = find_source_images(source_dir)
    if not images:
        print(f"{C.YELLOW}  ! No images found in: {source_dir}{C.NC}")
        print(f"    Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        sys.exit(0)

    # --- Parse format options ---
    output_format = None
    output_quality = None
    if args.format:
        fmt_name, fmt_quality = parse_format_spec(args.format)
        if fmt_name not in EXTENSION_MAP:
            print(f"{C.RED}  X Unknown format: '{fmt_name}'{C.NC}")
            print(f"    Supported: {', '.join(EXTENSION_MAP.keys())}")
            sys.exit(1)
        output_format = fmt_name
        output_quality = fmt_quality

    also_webp_quality = args.also_webp
    also_avif_quality = args.also_avif

    # --- Check external tools ---
    use_cwebp = has_cwebp()
    use_avifenc = has_avifenc()

    # --- Print summary ---
    by_label = "widths" if args.by == "width" else "heights"
    print(f"  {C.GREEN}Source:{C.NC}    {source_dir}")
    print(f"  {C.GREEN}Output:{C.NC}    {output_dir}")
    print(f"  {C.GREEN}Images:{C.NC}    {len(images)}")
    print(f"  {C.GREEN}Sizes:{C.NC}     {', '.join(str(s) + 'px' for s in sizes)} ({by_label})")
    print(f"  {C.GREEN}Label:{C.NC}     {'840w' if args.label == 'after' else 'w840'} style")

    if output_format:
        q_str = f":{output_quality}" if output_quality else ""
        print(f"  {C.GREEN}Format:{C.NC}    {output_format}{q_str}")
    else:
        print(f"  {C.GREEN}Format:{C.NC}    keep original")

    if also_webp_quality is not None:
        engine = "cwebp" if use_cwebp else "Pillow"
        print(f"  {C.GREEN}+WebP:{C.NC}     quality {also_webp_quality} ({engine})")
    if also_avif_quality is not None:
        engine = "avifenc" if use_avifenc else "Pillow"
        print(f"  {C.GREEN}+AVIF:{C.NC}     quality {also_avif_quality} ({engine})")
    if not args.keep_exif:
        print(f"  {C.DIM}EXIF metadata will be stripped{C.NC}")
    if args.allow_upscale:
        print(f"  {C.YELLOW}! Upscale allowed{C.NC}")

    print()

    # --- Dry run ---
    if args.dry_run:
        print(f"  {C.YELLOW}DRY RUN — nothing will be saved{C.NC}")
        print()
        total = 0
        for img_path in images:
            base = img_path.stem
            ext = img_path.suffix.lower()
            out_ext = EXTENSION_MAP.get(output_format, ext) if output_format else ext
            for size in sizes:
                name = build_output_name(base, size, args.by, args.label, out_ext)
                print(f"    {img_path.name} -> {name}")
                total += 1
                if also_webp_quality is not None and out_ext != ".webp":
                    wname = build_output_name(base, size, args.by, args.label, ".webp")
                    print(f"    {img_path.name} -> {wname}")
                    total += 1
                if also_avif_quality is not None and out_ext != ".avif":
                    aname = build_output_name(base, size, args.by, args.label, ".avif")
                    print(f"    {img_path.name} -> {aname}")
                    total += 1
        print()
        print(f"  {C.DIM}Total files to be created: {total}{C.NC}")
        print()
        return

    # --- Create output directory ---
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Process ---
    total_created = 0
    total_skipped = 0
    total_errors = 0
    total_bytes = 0

    for img_path in images:
        print(f"  {C.BOLD}{img_path.name}{C.NC}")

        try:
            img = Image.open(img_path)
        except Exception as e:
            print(f"    {C.RED}X Cannot open: {e}{C.NC}")
            total_errors += 1
            continue

        # Convert palette images early
        if img.mode == "P":
            img = img.convert("RGBA")

        exif_data = None
        if args.keep_exif:
            try:
                exif_data = img.info.get("exif")
            except Exception:
                pass

        base = img_path.stem
        src_ext = img_path.suffix.lower()

        for size in sizes:
            # --- Resize ---
            resized = resize_image(img, size, args.by, args.allow_upscale)

            if resized is None:
                dim = img.size[0] if args.by == "width" else img.size[1]
                label = "width" if args.by == "width" else "height"
                print(f"    {C.YELLOW}! {size}px skipped"
                      f" (source {label} is only {dim}px){C.NC}")
                total_skipped += 1
                continue

            # --- Determine output format ---
            if output_format:
                out_ext = EXTENSION_MAP[output_format]
                out_pil_fmt = FORMAT_MAP[out_ext]
                out_quality = output_quality
            else:
                out_ext = src_ext
                out_pil_fmt = FORMAT_MAP.get(src_ext, "PNG")
                out_quality = None

            # --- Save main format ---
            save_img = prepare_for_save(resized, out_pil_fmt)
            out_name = build_output_name(base, size, args.by, args.label, out_ext)
            out_path = output_dir / out_name
            save_kwargs = get_save_kwargs(out_pil_fmt, out_quality,
                                          args.keep_exif, exif_data)

            try:
                save_img.save(out_path, out_pil_fmt, **save_kwargs)
                fsize = out_path.stat().st_size
                total_bytes += fsize
                total_created += 1
                print(f"    {C.GREEN}+ {out_name}{C.NC}"
                      f" {C.DIM}({format_size(fsize)}){C.NC}")
            except Exception as e:
                print(f"    {C.RED}X {out_name}: {e}{C.NC}")
                total_errors += 1
                continue

            # --- Also WebP ---
            if also_webp_quality is not None and out_ext != ".webp":
                webp_name = build_output_name(base, size, args.by,
                                               args.label, ".webp")
                webp_path = output_dir / webp_name
                success = False

                # Try cwebp first
                if use_cwebp and out_ext in (".png", ".jpg", ".jpeg"):
                    success = convert_with_cwebp(
                        str(out_path), str(webp_path), also_webp_quality)

                # Fallback to Pillow
                if not success:
                    try:
                        webp_img = prepare_for_save(resized, "WEBP")
                        wkw = get_save_kwargs("WEBP", also_webp_quality, False)
                        webp_img.save(webp_path, "WEBP", **wkw)
                        success = True
                    except Exception as e:
                        print(f"    {C.RED}X {webp_name}: {e}{C.NC}")
                        total_errors += 1

                if success and webp_path.exists():
                    fsize = webp_path.stat().st_size
                    total_bytes += fsize
                    total_created += 1
                    tag = " [cwebp]" if use_cwebp else ""
                    print(f"    {C.GREEN}+ {webp_name}{C.NC}"
                          f" {C.DIM}({format_size(fsize)}){tag}{C.NC}")

            # --- Also AVIF ---
            if also_avif_quality is not None and out_ext != ".avif":
                avif_name = build_output_name(base, size, args.by,
                                               args.label, ".avif")
                avif_path = output_dir / avif_name
                success = False

                # Try avifenc first
                if use_avifenc and out_ext in (".png", ".jpg", ".jpeg"):
                    success = convert_with_avifenc(
                        str(out_path), str(avif_path), also_avif_quality)

                # Fallback to Pillow
                if not success:
                    try:
                        avif_img = prepare_for_save(resized, "AVIF")
                        akw = get_save_kwargs("AVIF", also_avif_quality, False)
                        avif_img.save(avif_path, "AVIF", **akw)
                        success = True
                    except Exception as e:
                        print(f"    {C.RED}X {avif_name}: {e}{C.NC}")
                        total_errors += 1

                if success and avif_path.exists():
                    fsize = avif_path.stat().st_size
                    total_bytes += fsize
                    total_created += 1
                    tag = " [avifenc]" if use_avifenc else ""
                    print(f"    {C.GREEN}+ {avif_name}{C.NC}"
                          f" {C.DIM}({format_size(fsize)}){tag}{C.NC}")

        img.close()
        print()

    # --- Summary ---
    print(f"{C.BLUE}{'=' * 60}{C.NC}")
    print(f"  {C.GREEN}+ Created: {total_created} files"
          f" ({format_size(total_bytes)}){C.NC}")
    if total_skipped > 0:
        print(f"  {C.YELLOW}! Skipped: {total_skipped}"
              f" (upscale protection){C.NC}")
    if total_errors > 0:
        print(f"  {C.RED}X Errors: {total_errors}{C.NC}")
    print(f"  {C.DIM}Output: {output_dir}{C.NC}")
    print(f"{C.BLUE}{'=' * 60}{C.NC}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="responsizer",
        description="Batch image resizer for srcset workflows.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  responsizer 840,420,330
  responsizer 840,420 --also-webp 85
  responsizer 840,420 --format webp:85 --source ./imgs
  responsizer 840,420 --also-webp 85 --also-avif 75
  responsizer --preset hero
        """,
    )

    parser.add_argument(
        "sizes", nargs="?", default=None,
        help="Sizes in pixels, comma-separated (e.g. 840,420,330)",
    )
    parser.add_argument(
        "--source", default=".",
        help="Source directory with images (default: current directory)",
    )
    parser.add_argument(
        "--output", default="./output",
        help="Output directory (default: ./output)",
    )
    parser.add_argument(
        "--by", choices=["width", "height"], default="width",
        help="Resize by width or height (default: width)",
    )
    parser.add_argument(
        "--label", choices=["after", "before"], default="after",
        help="Label position: after = 840w, before = w840 (default: after)",
    )
    parser.add_argument(
        "--format", default=None,
        help="Force output format, e.g. 'webp:85', 'jpg:90', 'png'",
    )
    parser.add_argument(
        "--also-webp", type=int, default=None, metavar="QUALITY",
        help="Also generate WebP copies with given quality (0-100)",
    )
    parser.add_argument(
        "--also-avif", type=int, default=None, metavar="QUALITY",
        help="Also generate AVIF copies with given quality (0-100)",
    )
    parser.add_argument(
        "--allow-upscale", action="store_true",
        help="Allow upscaling images (default: skip)",
    )
    parser.add_argument(
        "--keep-exif", action="store_true",
        help="Keep EXIF metadata (default: strip)",
    )
    parser.add_argument(
        "--preset", default=None,
        help="Load sizes from a preset in .responsizer.json",
    )
    parser.add_argument(
        "--config", type=Path, default=None,
        help="Path to config file (default: .responsizer.json)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be done without saving anything",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"responsizer {VERSION}",
    )

    args = parser.parse_args()

    if not args.sizes and not args.preset:
        parser.print_help()
        print()
        print(f"{C.RED}  X Specify sizes or --preset{C.NC}")
        print(f"    Example: responsizer 840,420,330")
        print()
        sys.exit(1)

    process(args)


if __name__ == "__main__":
    main()
