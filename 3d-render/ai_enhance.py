"""Нейросетевая доработка рендера «до фото» (бесплатно, открытые модели, CPU).
Stable Diffusion 1.5 (Realistic Vision 5.1) + ControlNet Tile: нейросеть меняет фактуру
(трава, штукатурка, листья, свет), а ControlNet Tile держит контуры — окна, двери, кровля остаются на местах.
Кадр обрабатывается кусками 768×768 с перекрытием и сшивается плавной маской.

python ai_enhance.py <вход.png> <выход.jpg> [strength=0.35] [steps=24]
"""
import sys, math, os, time
import numpy as np
import torch
from PIL import Image
from diffusers import ControlNetModel, StableDiffusionControlNetImg2ImgPipeline, AutoencoderKL, DPMSolverMultistepScheduler
from huggingface_hub import hf_hub_download

src, dst = sys.argv[1], sys.argv[2]
STRENGTH = float(sys.argv[3]) if len(sys.argv) > 3 else 0.35
STEPS = int(sys.argv[4]) if len(sys.argv) > 4 else 24
TILE, OVER = 768, 160
torch.set_num_threads(os.cpu_count())

PROMPT = ("professional architectural photograph of a real house, real estate photography, white textured stucco facade, "
          "dark grey plinth, white pvc windows with warm interior light and curtains, corrugated metal roof, "
          "manicured fresh green lawn with natural grass blades, lavender and boxwood bushes, golden hour warm sunlight, "
          "soft natural shadows, photorealistic, highly detailed, sharp focus, DSLR, 35mm photo")
NEG = ("cartoon, cgi, 3d render, plastic, illustration, painting, drawing, anime, blurry, lowres, noise, deformed, "
       "distorted geometry, extra windows, text, watermark, logo, people, person")

dt = torch.float32
cn = ControlNetModel.from_pretrained("lllyasviel/control_v11f1e_sd15_tile", torch_dtype=dt)
vae = AutoencoderKL.from_pretrained("stabilityai/sd-vae-ft-mse", torch_dtype=dt)
pipe = StableDiffusionControlNetImg2ImgPipeline.from_pretrained("SG161222/Realistic_Vision_V5.1_noVAE", controlnet=cn, vae=vae, torch_dtype=dt,
                                                                safety_checker=None, requires_safety_checker=False)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True, algorithm_type="dpmsolver++", solver_type="midpoint", final_sigmas_type="sigma_min")
pipe.set_progress_bar_config(disable=True)

img = Image.open(src).convert("RGB")
W, H = img.size
src_np = np.asarray(img).astype(np.float32)
acc = np.zeros_like(src_np); wsum = np.zeros((H, W, 1), np.float32)

def starts(n, t, o):
    if n <= t: return [0]
    k = math.ceil((n - o) / (t - o)); step = (n - t) / (k - 1)
    return [round(i * step) for i in range(k)]

ramp = np.minimum(np.linspace(0, 1, OVER), 1)
def weight(tw, th):
    wx = np.ones(tw, np.float32); wy = np.ones(th, np.float32)
    wx[:OVER] = ramp; wx[-OVER:] = ramp[::-1]; wy[:OVER] = ramp; wy[-OVER:] = ramp[::-1]
    return np.clip(np.outer(wy, wx), 1e-3, 1)[..., None]

gen = torch.Generator().manual_seed(7)
t0 = time.time(); xs, ys = starts(W, TILE, OVER), starts(H, TILE, OVER)
for y in ys:
    for x in xs:
        tile = img.crop((x, y, x + TILE, y + TILE))
        out = pipe(prompt=PROMPT, negative_prompt=NEG, image=tile, control_image=tile, strength=STRENGTH,
                   num_inference_steps=STEPS, guidance_scale=6.0, controlnet_conditioning_scale=1.0, generator=gen).images[0]
        o = np.asarray(out.resize(tile.size, Image.LANCZOS)).astype(np.float32)
        w = weight(*tile.size)
        acc[y:y + TILE, x:x + TILE] += o * w; wsum[y:y + TILE, x:x + TILE] += w
        print(f"tile {x},{y} done {time.time() - t0:.0f}s", flush=True)
res = acc / wsum
Image.fromarray(np.clip(res, 0, 255).astype(np.uint8)).save(dst, quality=94)
print("OK", dst, f"{time.time() - t0:.0f}s")
