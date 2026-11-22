"""Safe resolution of JSON media references for optional SDL windows."""
from pathlib import Path

def resolve_media(root, reference):
    if not reference or not root:
        return None
    root = Path(root).resolve()
    ref = Path(str(reference))
    candidates = [root / ref, root / 'images' / ref, root / 'audio' / ref, root / 'media' / ref, root / 'content_library' / ref, root / 'games_media' / ref]
    for candidate in candidates:
        path = candidate.resolve()
        if path.is_relative_to(root) and path.is_file():
            return path
    return None

def load_image(pygame, path, max_size):
    if not path:
        return None
    try:
        image = pygame.image.load(str(path)).convert_alpha()
        rect = image.get_rect().fit(pygame.Rect(0, 0, *max_size))
        return pygame.transform.smoothscale(image, (max(1,rect.width),max(1,rect.height)))
    except (pygame.error, OSError, ValueError):
        return None
