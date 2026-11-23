"""Unified subject content store. Existing progress/database never moved."""
from pathlib import Path
import json,shutil

SUBJECTS={'en':'tieng_anh','vi':'tieng_viet'}
KINDS=('lessons','questions','vocab','blocks')
# Skip repeated legacy image migration within the same process.
# A fresh application launch still performs the compatibility scan.
_SCANNED_IMAGE_FOLDERS=set()
def prepare_subject(data_root,language,bundle_root,legacy_root=None):
    data_root=Path(data_root);bundle_root=Path(bundle_root)
    if language not in SUBJECTS:raise ValueError('Unknown language')
    folder=data_root/'mon_hoc'/SUBJECTS[language]
    folder.mkdir(parents=True,exist_ok=True)
    output=folder/'content_library';output.mkdir(exist_ok=True)
    (folder/'images').mkdir(exist_ok=True)
    demo=bundle_root/'DU_LIEU_MAU'/SUBJECTS[language]/'hinh_mau.png'
    if demo.exists() and not (folder/'images'/'hinh_mau.png').exists():shutil.copy2(demo,folder/'images'/'hinh_mau.png')
    previous=Path(legacy_root) if legacy_root is not None else data_root
    old_subject=previous/'mon_hoc'/SUBJECTS[language]
    legacy=previous/'vi'/'content_library' if language=='vi' else previous/'content_library'
    bundled=bundle_root/'vietnamese_levels' if language=='vi' else bundle_root/'content_library'/'demo_levels'
    for kind in KINDS:
        dest=output/f'level_{kind}.json'
        if dest.exists():continue
        source=old_subject/'content_library'/f'level_{kind}.json'
        if not source.is_file():source=legacy/f'level_{kind}.json'
        if not source.is_file():source=bundled/f'{kind}.json'
        if source.is_file():shutil.copy2(source,dest)
        else:dest.write_text('[]',encoding='utf8')
    scan_key=(str(folder.resolve()),str(previous.resolve()))
    if scan_key not in _SCANNED_IMAGE_FOLDERS:
      for image_dir in (old_subject/'images',legacy/'images',legacy/'media',previous/'content_library'/'images'):
        if image_dir.exists():
            for old in image_dir.rglob('*'):
                if old.is_file() and old.suffix.lower() in ('.png','.jpg','.jpeg','.gif','.webp'):
                    destination=folder/'images'/old.name
                    if not destination.exists():shutil.copy2(old,destination)
      _SCANNED_IMAGE_FOLDERS.add(scan_key)
    return folder

def subject_image(subject_dir,relative):
    if not isinstance(relative,str) or not relative.strip():return None
    base=Path(subject_dir).resolve();rel=Path(relative)
    if rel.is_absolute():return None
    for candidate in (base/rel,base/'images'/rel,base/'content_library'/rel):
        resolved=candidate.resolve()
        if resolved.is_relative_to(base) and resolved.is_file():return resolved
    return None
