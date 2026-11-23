"""Shared image sizing for Studio and the question renderers."""
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageOps


@lru_cache(maxsize=24)
def _load(path, mtime, width, height, fit):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert('RGBA')
    size = (width, height)
    if fit == 'cover':
        return ImageOps.fit(image, size, Image.Resampling.LANCZOS)
    if fit == 'stretch':
        return image.resize(size, Image.Resampling.LANCZOS)
    return ImageOps.contain(image, size, Image.Resampling.LANCZOS)


def fitted_image(path, size, fit='contain'):
    source = Path(path)
    width, height = (max(1, int(value)) for value in size)
    return _load(source, source.stat().st_mtime_ns, width, height, fit)


def _rect(geometry, default):
    import pygame

    return pygame.Rect(*(geometry.get(key) or fallback if key in ('width', 'height')
                         else geometry.get(key, fallback)
                         for key, fallback in zip(('x', 'y', 'width', 'height'), default)))


def pygame_image(path, geometry, default):
    """Return the authored image, centered in its frame, and the frame itself."""
    import pygame

    frame = _rect(geometry, default)
    image = fitted_image(path, frame.size, geometry.get('image_fit', 'contain'))
    pixels = pygame.image.frombytes(image.tobytes(), image.size, 'RGBA')
    return pixels, pixels.get_rect(center=frame.center), frame
