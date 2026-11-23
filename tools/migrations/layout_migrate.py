"""Migrate question layout values in UTF-8 JSON while preserving surrounding bytes."""
import argparse
import json
import os
from pathlib import Path
import stat
from tempfile import NamedTemporaryFile

from tuhoc.studio.question_layout_store import layout_v2, layout_v3, validate_layout


def _spans(text):
    """Yield value spans for layout fields owned by question objects."""
    decoder = json.JSONDecoder()

    def whitespace(offset):
        while offset < len(text) and text[offset] in ' \t\r\n':
            offset += 1
        return offset

    def read(offset):
        offset = whitespace(offset)
        if text[offset] not in '[{':
            value, end = decoder.raw_decode(text, offset)
            return value, end, []
        array = text[offset] == '['
        endchar = ']' if array else '}'
        value = [] if array else {}
        fields = {}
        children = []
        cursor = whitespace(offset + 1)
        while text[cursor] != endchar:
            key = None
            if not array:
                key, end = decoder.raw_decode(text, cursor)
                cursor = whitespace(whitespace(end) + 1)
            item, end, nested = read(cursor)
            if array:
                value.append(item)
            else:
                if key in fields:
                    raise ValueError(f'Khóa JSON trùng: {key!r}.')
                fields[key] = (cursor, end)
                value[key] = item
            children.extend(nested)
            cursor = whitespace(end)
            if text[cursor] == endchar:
                break
            cursor = whitespace(cursor + 1)
        if not array and isinstance(value.get('type'), str) and 'layout' in fields:
            if 'prompt' in value or 'answer' in value or isinstance(value['layout'], dict):
                children.append((*fields['layout'], value['layout']))
        return value, cursor + 1, children

    json.loads(text)
    return sorted(read(0)[2])


def migrate_bytes(original, *, version=2):
    """Return migrated UTF-8 bytes and count, without touching a file."""
    text = original.decode('utf-8-sig')
    prefix = b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b''
    edits = []
    for start, end, layout in _spans(text):
        checked = validate_layout(layout)
        if checked and checked.get('version', 1) < version:
            convert = layout_v3 if version == 3 else layout_v2
            encoded = json.dumps(convert(checked), ensure_ascii=False, separators=(',', ':'))
            edits.append((start, end, encoded))
    parts, cursor = [], 0
    for start, end, encoded in edits:
        if cursor > start:
            raise ValueError('Các vùng bố cục JSON bị chồng lấn.')
        parts.extend((text[cursor:start], encoded))
        cursor = end
    parts.append(text[cursor:])
    migrated = prefix + ''.join(parts).encode('utf-8')
    for _, _, layout in _spans(migrated.decode('utf-8-sig')):
        validate_layout(layout)
    return migrated, len(edits)


def _replace(path, expected, content):
    tmp_path = None
    try:
        with NamedTemporaryFile(dir=path.parent, prefix=path.name + '.', suffix='.tmp', delete=False) as tmp:
            tmp_path = Path(tmp.name)
            if hasattr(os, 'fchmod'):
                os.fchmod(tmp.fileno(), stat.S_IMODE(path.stat().st_mode))
            tmp.write(content)
            tmp.flush()
            os.fsync(tmp.fileno())
        if tmp_path.read_bytes() != content:
            raise OSError('Bản tạm khác dữ liệu dự kiến.')
        json.loads(tmp_path.read_bytes())
        if path.read_bytes() != expected:
            raise OSError('Tệp nguồn đã thay đổi trong lúc xử lý.')
        os.replace(tmp_path, path)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def migrate_file(path, *, version=2):
    path = Path(path).resolve(strict=True)
    original = path.read_bytes()
    updated, count = migrate_bytes(original, version=version)
    if not count:
        return 0
    backup = path.with_name(path.name + '.bak')
    try:
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0),
                     stat.S_IMODE(path.stat().st_mode))
        with os.fdopen(fd, 'wb') as copy:
            copy.write(original)
            copy.flush()
            os.fsync(copy.fileno())
    except FileExistsError:
        pass
    if backup.read_bytes() != original:
        raise OSError(f'Bản sao lưu hiện có khác nguồn: {backup}')
    _replace(path, original, updated)
    actual = path.read_bytes()
    if actual != updated:
        _replace(path, actual, backup.read_bytes())
        if path.read_bytes() != original:
            raise OSError('Không xác nhận được bản đã phục hồi.')
        raise OSError('Kiểm tra sau di trú thất bại. Đã phục hồi bản gốc.')
    return count


def restore_file(path):
    path = Path(path).resolve(strict=True)
    backup = path.with_name(path.name + '.bak')
    original = backup.read_bytes()
    migrate_bytes(original)
    _replace(path, path.read_bytes(), original)
    if path.read_bytes() != original:
        raise OSError('Không xác nhận được bản đã phục hồi.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--restore', action='store_true')
    parser.add_argument('--version', type=int, choices=(2, 3), default=2)
    args = parser.parse_args()
    if args.restore:
        restore_file(args.path)
        print('Đã phục hồi:', args.path)
    else:
        print('Số bố cục đã di trú:', migrate_file(args.path, version=args.version))


if __name__ == '__main__':
    main()
