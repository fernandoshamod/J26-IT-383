"""Read-only dataset release contract for future preprocessing/training callers.

This module does not preprocess data or train models. Call verified_release() before
reading inputs and assert_experiment_output() before every output write.
"""
import hashlib
import json
from pathlib import Path
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / 'dataset_releases'


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def assert_experiment_output(path, releases_root=RELEASES):
    """Reject outputs within releases or their ancestors (including symlink aliases)."""
    target = Path(path).resolve()
    protected = Path(releases_root).resolve()
    if target == protected or target.is_relative_to(protected) or protected.is_relative_to(target):
        raise ValueError('immutable_release_output_forbidden:' + str(target))
    return target


def verified_release(release=RELEASES / 'v1.0'):
    release = Path(release).resolve()
    manifest = json.loads((release / 'RELEASE_MANIFEST.json').read_text(encoding='utf-8'))
    archive = release / manifest['release_archive']['file_name']
    if archive.resolve().parent != release:
        raise ValueError('archive_outside_release')
    if sha256(archive) != manifest['release_archive']['sha256']:
        raise ValueError('release_checksum_mismatch')
    if hasattr(stat, 'FILE_ATTRIBUTE_READONLY'):
        attributes = getattr(archive.stat(), 'st_file_attributes', None)
        if attributes is not None and not attributes & stat.FILE_ATTRIBUTE_READONLY:
            raise ValueError('release_not_read_only')
    with zipfile.ZipFile(archive, 'r') as package:
        package_manifest = json.loads(package.read('package_manifest.json'))
        if package_manifest['frozen_synthetic_configuration_sha256'] != manifest['configuration']['canonical_sha256']:
            raise ValueError('release_configuration_mismatch')
        if package_manifest['statistics'] != manifest['record_counts']:
            raise ValueError('release_counts_mismatch')
    return archive, manifest
