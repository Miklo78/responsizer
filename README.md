# RESPONSIZER

A command-line tool for batch generating multiple image sizes for responsive web design. If you're building websites with `srcset` or `<picture>` elements, you know the pain: for every image, you need 4, 6, sometimes 10+ size variants — each correctly sized, named, and optimized. Responsizer does this in a single command.

Drop your source images into a folder, tell Responsizer what widths (or heights) you need, and it generates all variants with consistent naming ready for your HTML. It can also produce WebP and AVIF copies alongside the originals for modern browsers.

Responsizer is a Python script that runs in the terminal. It requires Python and the Pillow library. It works on macOS, Windows, and Linux.

**Input:** `your-image.png` (2400×1600 px)

**Command:**
```bash
responsizer 1920,1280,960,640,320
```

**Output (in `output/` folder):**
```
your-image-1920w.png
your-image-1280w.png
your-image-960w.png
your-image-640w.png
your-image-320w.png
```

All images in the folder, all sizes, aspect ratio preserved, done.

---

## Usage

### Basic command

```bash
responsizer 1920,1280,960,640,320
```

Processes all images in the current directory (PNG, JPG, WebP, AVIF, GIF, TIFF, BMP), creates variants at the specified widths. Height is calculated automatically (preserves aspect ratio). Output goes to `./output/`.

### Specify source and output directories

```bash
responsizer 1920,1280,640,320 --source ./my-photos --output ./web-images
```

### Force output format

```bash
responsizer 1920,1280,640 --format webp:85
```

The number after the colon is quality (0–100). Works with:
- `webp:85` — WebP at quality 85
- `jpg:90` — JPEG at quality 90
- `png` — PNG (lossless, no quality setting)
- `avif:75` — AVIF at quality 75

### Generate WebP / AVIF copies alongside originals

The most practical option for modern web — you get the original format AND WebP and/or AVIF copies:

```bash
responsizer 1920,1280,640,320 --also-webp 85
```

Output:
```
your-image-1920w.png
your-image-1920w.webp
your-image-1280w.png
your-image-1280w.webp
your-image-640w.png
your-image-640w.webp
your-image-320w.png
your-image-320w.webp
```

Both WebP and AVIF at once:
```bash
responsizer 1920,1280,640 --also-webp 85 --also-avif 75
```

### Resize by height

Default is resize by width. If you need height-based sizing:

```bash
responsizer 1080,720,480 --by height
```

Output: `your-image-1080h.png`, `your-image-720h.png`, etc.

### Change naming style

Default style is `1280w` (number + letter). If you prefer `w1280` (letter + number):

```bash
responsizer 1920,1280,640 --label before
```

Output: `your-image-w1280.png` instead of `your-image-1280w.png`.

### Dry run (preview)

Want to see what would happen without creating any files?

```bash
responsizer 1920,1280,960,640,320 --dry-run
```

### Allow upscaling

Default behavior: if a source image is smaller than the requested size, that size is skipped (to avoid quality loss from upscaling). To override:

```bash
responsizer 1920,1280,640 --allow-upscale
```

### Keep EXIF metadata

Default: EXIF is stripped (smaller files, no GPS coordinates on the web). To keep it:

```bash
responsizer 1920,1280,640 --keep-exif
```

---

## All parameters

| Parameter | What it does | Default |
|-----------|-------------|---------|
| `1920,1280,640` | Sizes in pixels (required, or use `--preset`) | — |
| `--source ./dir` | Source directory | `.` (current) |
| `--output ./dir` | Output directory | `./output` |
| `--by width/height` | Resize by width or height | `width` |
| `--label after/before` | `1280w` or `w1280` style | `after` |
| `--format webp:85` | Force output format + quality | keep original |
| `--also-webp 85` | Also generate WebP copies | — |
| `--also-avif 75` | Also generate AVIF copies | — |
| `--allow-upscale` | Allow upscaling | skip |
| `--keep-exif` | Keep EXIF metadata | strip |
| `--preset hero` | Load sizes from config | — |
| `--config ./file` | Path to config file | `.responsizer.json` |
| `--dry-run` | Preview only, no files created | — |
| `--version` | Show version | — |

---

## Presets

Save your commonly used size sets so you don't have to type them every time.

Create a `.responsizer.json` file in your home directory or project folder:

```json
{
  "presets": {
    "hero": [1920, 1280, 960, 640, 320],
    "card": [960, 640, 480, 320],
    "thumb": [300, 150]
  }
}
```

Then just:
```bash
responsizer --preset hero
responsizer --preset card --also-webp 85
```

Responsizer looks for the config file in this order:
1. `--config /path/to/file.json` (if specified)
2. `.responsizer.json` in the current directory
3. `.responsizer.json` in the home directory (`~`)

---

## Smart renaming

Responsizer automatically detects if a filename already contains a size label.

**Input:** `banner-1920w.png`

```bash
responsizer 1280,960,640
```

**Output:**
```
banner-1280w.png  (NOT banner-1920w-1280w.png)
banner-960w.png
banner-640w.png
```

Works with both styles — detects `1920w`, `w1920`, `1080h`, and `h1080`.

---

## WebP and AVIF — better compression

Responsizer can use external tools for better compression if they are installed on your system. If not, it falls back to the built-in Pillow library (works fine, just slightly larger files).

When an external tool is used, you'll see `[cwebp]` or `[avifenc]` next to each file in the output.

**cwebp** (by Google, for WebP):
```bash
# macOS:
brew install webp

# Windows: download from https://developers.google.com/speed/webp/download

# Linux:
sudo apt install webp
```

**avifenc** (for AVIF):
```bash
# macOS:
brew install libavif

# Windows / Linux: download from https://github.com/AOMediaCodec/libavif/releases
```

Installing these tools is optional. Responsizer works without them.

---

## Supported formats

PNG, JPG/JPEG, WebP, AVIF, GIF, TIFF, BMP — as both input and output.

---

## Real-world examples

### Website reference screenshots
```bash
cd www/img/references/project/
responsizer 1920,1280,960,640,320 --also-webp 85
```

### E-commerce product photos
```bash
responsizer --preset product --also-webp 85 --also-avif 75 --source ./products
```

### Bulk conversion to WebP
```bash
responsizer 1920,1280,640 --format webp:85
```

### Preview before running
```bash
responsizer 1920,1280,960,640,320 --dry-run
```

---

## Installation

### 1. Install Python

**macOS:**
```bash
brew install python
```
(If you don't have Homebrew, install it from https://brew.sh)

**Windows:**
- Download from https://www.python.org/downloads/
- During installation, **check "Add Python to PATH"** (important!)
- Click Install

**Linux:**
```bash
sudo apt install python3 python3-pip
```

### 2. Install the Pillow library

**macOS:**
```bash
pip3 install Pillow --break-system-packages --user
```

This looks scary but it's safe — `--break-system-packages` simply bypasses a protection in newer Homebrew, and `--user` ensures Pillow is installed only in your user profile (`~/Library/Python/`), not system-wide. Nothing will break. To uninstall later: `pip3 uninstall Pillow`.

**Windows:**
```bash
pip install Pillow
```

**Linux:**
```bash
pip3 install Pillow
```
(Or `pip3 install --user Pillow` if you don't have root access.)

### 3. Download responsizer

Save `responsizer.py` wherever you like (e.g. `~/Tools/` or `C:\Tools\`).

### 4. Set up as a global command (so it works from any directory)

Without this step, you'd have to type `python3 /path/to/responsizer.py ...` every time. With this step, you just type `responsizer ...` from anywhere.

#### macOS

**Option A — wrapper script (recommended):**

```bash
# 1. Create a folder for your tools (if you don't have one):
mkdir -p ~/Tools

# 2. Move responsizer.py into it:
mv responsizer.py ~/Tools/responsizer.py

# 3. Create the global command (requires password once):
sudo bash -c 'echo "#!/bin/bash
python3 $HOME/Tools/responsizer.py \"\$@\"" > /usr/local/bin/responsizer'
sudo chmod +x /usr/local/bin/responsizer
```

Done. You type `responsizer 1920,1280,640` from anywhere. The password is only needed this one time during setup.

**Option B — alias in .zshrc (simpler, no sudo):**

```bash
# 1. Move the file:
mkdir -p ~/Tools
mv responsizer.py ~/Tools/responsizer.py

# 2. Open your terminal config:
nano ~/.zshrc

# 3. Add this line at the end of the file:
alias responsizer='python3 ~/Tools/responsizer.py'

# 4. Save and close:
#    - press Ctrl+X
#    - confirm with Y
#    - press Enter

# 5. Reload (or restart the terminal):
source ~/.zshrc
```

The difference: Option A creates an actual system command. Option B creates a shortcut only for your terminal. Both work the same way.

#### Windows

```powershell
# 1. Create a folder for tools:
mkdir C:\Tools

# 2. Move responsizer.py into it (via File Explorer or PowerShell):
Move-Item responsizer.py C:\Tools\responsizer.py

# 3. Open your PowerShell profile:
notepad $PROFILE
```

If prompted "File does not exist, create it?", click Yes.

```powershell
# 4. Add this line to the file:
function responsizer { python C:\Tools\responsizer.py @args }

# 5. Save the file and close Notepad.

# 6. Restart PowerShell.
```

You can now type `responsizer 1920,1280,640` from anywhere.

**Note:** If PowerShell shows an execution policy error, run this once:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Linux

Same as macOS, just edit `~/.bashrc` instead of `~/.zshrc`:

```bash
mkdir -p ~/Tools
mv responsizer.py ~/Tools/responsizer.py
echo "alias responsizer='python3 ~/Tools/responsizer.py'" >> ~/.bashrc
source ~/.bashrc
```

#### Verify

Open a new terminal and run:

```bash
responsizer --version
```

You should see `responsizer 0.1.0`. If so, everything works.

---

## Troubleshooting

### "python: command not found"
On macOS/Linux try `python3` instead of `python`. If that doesn't work either, Python is not installed — see the Installation section.

### "No module named PIL"
Pillow is not installed. See Installation, step 2.

### Images are skipped with "upscale protection"
The source image is smaller than the requested size. Either use smaller dimensions, or add `--allow-upscale`.

### Colors don't work on Windows
Use Windows Terminal (recommended) instead of the old cmd.exe.

---

## Version history

- **0.1.0** — Initial release. Resize, WebP, AVIF, presets, smart rename.
