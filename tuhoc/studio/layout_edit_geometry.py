"""Design-space movement, snapping and distribution shared by Studio actions."""
from tuhoc.studio.layout_render import PAGE_LIMIT


def edges(rect, axis):
    start, size = ('x', 'width') if axis == 'x' else ('y', 'height')
    return rect[start], rect[start] + rect[size] / 2, rect[start] + rect[size]


def bounds(rectangles):
    x = min(rect['x'] for rect in rectangles)
    y = min(rect['y'] for rect in rectangles)
    right = max(rect['x'] + rect['width'] for rect in rectangles)
    bottom = max(rect['y'] + rect['height'] for rect in rectangles)
    return dict(x=x, y=y, width=right-x, height=bottom-y)


def constrain(rect, dx, dy):
    return (max(-rect['x'], min(1-rect['x']-rect['width'], dx)),
            max(-rect['y'], min(PAGE_LIMIT-rect['y']-rect['height'], dy)))


def snap_axis(rect, axis, delta, others, threshold, guides):
    moving = tuple(value + delta for value in edges(rect, axis))
    targets = [*guides]
    for other in others:
        anchors = edges(other, axis)
        if anchors[-1] >= moving[0]-threshold and anchors[0] <= moving[-1]+threshold:
            targets.extend(anchors)
    if targets:
        distance, target = min(((target-value, target) for target in targets for value in moving),
                               key=lambda pair: abs(pair[0]))
        if abs(distance) <= threshold:
            return delta+distance, target, distance
    return delta, None, 0


def arrange(rectangles, axis, position):
    """Return coordinates with a shared edge/center, or equal gaps inside the group."""
    extent = bounds(list(rectangles.values()))
    size = 'width' if axis == 'x' else 'height'
    start = extent[axis]
    if position == 'space':
        if len(rectangles) < 3:
            return {}
        ordered = sorted(rectangles, key=lambda key: rectangles[key][axis])
        gap = (extent[size]-sum(rectangles[key][size] for key in ordered))/(len(ordered)-1)
        result = {}
        for key in ordered:
            result[key] = {**rectangles[key],axis:start}
            start += rectangles[key][size]+gap
        return result
    return {key:{**rect,axis:start+(extent[size]-rect[size])*position}
            for key,rect in rectangles.items()}
