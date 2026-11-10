"""PDF «Render ko'rinishi» как в образце офиса: A4 вертикально, по одному виду на лист, картинка во всю ширину по центру.
python render_pdf.py <папка_с_png> <файл.pdf>"""
import sys, glob, os
from PIL import Image
src, out = sys.argv[1], sys.argv[2]
DPI = 200
W, H = int(8.268 * DPI), int(11.693 * DPI)
pages = []
for f in sorted(glob.glob(os.path.join(src, "*.png"))):
    im = Image.open(f).convert("RGB")
    im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
    pg = Image.new("RGB", (W, H), "white"); pg.paste(im, (0, (H - im.height) // 2)); pages.append(pg)
pages[0].save(out, save_all=True, append_images=pages[1:], resolution=DPI, quality=92)
print("PDF", out, len(pages), "листов")
