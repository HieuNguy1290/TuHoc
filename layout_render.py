"""Shared coordinate space for authoring and Pygame."""
DESKTOP = (960, 640)
MOBILE = (390, 760)
PAGE_LIMIT = 4
HORIZONTAL = ('x', 'width')
VERTICAL = ('y', 'height')
GEOMETRY = HORIZONTAL + VERTICAL
SCREENS = {'desktop': DESKTOP, 'mobile': MOBILE}


def to_pixels(values, screen):
    width, height = screen
    sizes = {field: width for field in HORIZONTAL} | {field: height for field in VERTICAL}
    return {field: round(value * sizes[field]) if field in sizes else int(value) if field == 'font_size' else value
            for field, value in values.items()}


def to_relative(values, screen):
    width, height = screen
    sizes = {field: width for field in HORIZONTAL} | {field: height for field in VERTICAL}
    return {field: value / sizes[field] if field in sizes else value
            for field, value in values.items()}


def fit_pixels(rect, screen):
    """Keep rounded sizes inside the viewport's width and page extent."""
    width, height = screen
    result = dict(rect)
    for coordinate, size, limit in (('x', 'width', width),
                                    ('y', 'height', height * PAGE_LIMIT)):
        if coordinate in result and size in result:
            result[size] = min(result[size], limit - result[coordinate])
    return result
