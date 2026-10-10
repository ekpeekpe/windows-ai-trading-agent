"""Temporary local branding for NSIS build. Replace before commercial release."""
from pathlib import Path
from PIL import Image, ImageDraw

folder = Path(__file__).resolve().parents[1] / "src-tauri" / "icons"
folder.mkdir(parents=True, exist_ok=True)
icon = Image.new("RGBA", (256, 256), (22, 31, 48, 255))
draw = ImageDraw.Draw(icon)
draw.line([(24, 173), (68, 121), (117, 147), (166, 76), (231, 53)], fill=(82, 214, 174, 255), width=12)
icon.save(folder / "icon.png")
icon.save(folder / "icon.ico", format="ICO", sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
print("Generated unsigned pilot icon assets:", folder)
