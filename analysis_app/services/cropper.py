# analysis_app/services/cropper.py

import os
import uuid
from pathlib import Path
from PIL import Image
from django.conf import settings


def crop_region_from_page(page_image_name: str, x1: float, y1: float, x2: float, y2: float) -> str:
  
    full_path = Path(settings.MEDIA_ROOT) / page_image_name
    img = Image.open(full_path)
    width, height = img.size

    left = int(x1 * width)
    upper = int(y1 * height)
    right = int(x2 * width)
    lower = int(y2 * height)

    left = max(0, min(left, width))
    right = max(0, min(right, width))
    upper = max(0, min(upper, height))
    lower = max(0, min(lower, height))

    if right <= left or lower <= upper:
        raise ValueError("Invalid crop region")

    cropped = img.crop((left, upper, right, lower))

    out_dir = Path(settings.MEDIA_ROOT) / "analysis/crops/"
    out_dir.mkdir(parents=True, exist_ok=True)

    import uuid
    filename = f"{uuid.uuid4().hex}.png"
    out_path = out_dir / filename
    cropped.save(out_path)

    rel_path = str(out_path.relative_to(settings.MEDIA_ROOT))
    return rel_path