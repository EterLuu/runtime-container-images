#!/usr/bin/env python3
"""Helpers for runtime image metadata used by local scripts and CI."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

DEFAULT_METADATA = "image_publish_version.json"
IMAGES_DIR = "images"
KNOWN_CHIPS = ("910b", "310p", "910", "950", "a3")
DEFAULT_ARCHES = [
    {
        "platform": "linux/amd64",
        "runner": "ubuntu-latest",
        "artifact_arch": "amd64",
    },
    {
        "platform": "linux/arm64",
        "runner": "ubuntu-22.04-arm",
        "artifact_arch": "arm64",
    },
]
CUDA_DEFAULT_ARCHES = [
    {
        "platform": "linux/amd64",
        "runner": "ubuntu-latest",
        "artifact_arch": "amd64",
    },
]
TAG_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")


class MetadataError(ValueError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_metadata(metadata_path: str) -> dict:
    path = Path(metadata_path)
    if not path.is_absolute():
        path = repo_root() / path
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise MetadataError(f"metadata file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise MetadataError(f"metadata file is not valid JSON: {path}: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("versions"), list):
        raise MetadataError("metadata must contain a top-level 'versions' array")
    return data


def extract_base_image(dockerfile: Path) -> str:
    base_image_arg = ""
    from_image = ""
    for raw_line in dockerfile.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("ARG BASE_IMAGE="):
            base_image_arg = line.split("=", 1)[1].strip()
        elif line.startswith("FROM ") and "${BASE_IMAGE}" not in line:
            from_image = line.split(None, 1)[1].strip()
    return base_image_arg or from_image


def infer_chip(tag: str) -> str:
    for chip in KNOWN_CHIPS:
        if f"-{chip}-" in tag:
            return chip
    return ""


def infer_version(tag: str, chip: str) -> str:
    if chip and f"-{chip}-" in tag:
        return tag.split(f"-{chip}-", 1)[0]
    return tag.split("-", 1)[0]


def repository_suffix(entry: dict) -> str:
    image_platform = entry.get("image_platform")
    image_flavor = entry.get("image_flavor")
    if not image_platform or not image_flavor:
        return "runtime-image"
    return f"{image_platform}-{image_flavor}"


def entry_version(entry: dict) -> str:
    return entry.get("image_version") or ""


def default_arches_for(image_flavor: str) -> list[dict]:
    if image_flavor == "cuda":
        return CUDA_DEFAULT_ARCHES
    return DEFAULT_ARCHES


def entry_image_key(entry: dict) -> str:
    return entry.get("image_key") or entry.get("path", "")


def artifact_key(entry: dict) -> str:
    value = entry_image_key(entry) or entry["tags"][0]
    value = value.removeprefix(f"{IMAGES_DIR}/")
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")


def discover_entries(data: dict, root: Path) -> list[dict]:
    configs = data["versions"]
    by_path = {}
    by_tag = {}
    for config in configs:
        if not isinstance(config, dict):
            continue
        if isinstance(config.get("path"), str):
            by_path[config["path"]] = config
        for tag in config.get("tags", []):
            if isinstance(tag, str):
                by_tag[tag] = config

    entries = []
    images_root = root / IMAGES_DIR
    for dockerfile in sorted(images_root.glob("*/*/*/Dockerfile")):
        image_dir = dockerfile.parent
        rel_path = image_dir.relative_to(root).as_posix()
        parts = image_dir.relative_to(images_root).parts
        if len(parts) != 3:
            continue

        image_platform, image_flavor, tag = parts
        config = by_path.get(rel_path, by_tag.get(tag, {}))
        entry = copy.deepcopy(config)
        chip = entry.get("chip") or infer_chip(tag)

        entry.update(
            {
                "path": rel_path,
                "image_key": entry.get("image_key", rel_path),
                "image_platform": entry.get("image_platform", image_platform),
                "image_flavor": entry.get("image_flavor", image_flavor),
                "tags": entry.get("tags", [tag]),
                "base_image": entry.get("base_image") or extract_base_image(dockerfile),
                "chip": chip,
                "image_version": entry_version(entry) or infer_version(tag, chip),
                "arches": entry.get("arches") or default_arches_for(image_flavor),
            }
        )
        entry["repository_suffix"] = entry.get(
            "repository_suffix"
        ) or repository_suffix(entry)
        entries.append(entry)

    configured_paths = {entry["path"] for entry in entries}
    for config in configs:
        if not isinstance(config, dict):
            continue
        path = config.get("path")
        if not isinstance(path, str) or path in configured_paths:
            continue
        if (root / path / "Dockerfile").is_file():
            entry = copy.deepcopy(config)
            parts = Path(path).parts
            if len(parts) >= 4 and parts[0] == IMAGES_DIR:
                entry.setdefault("image_platform", parts[1])
                entry.setdefault("image_flavor", parts[2])
            entry.setdefault("image_key", path)
            entry.setdefault("image_version", entry_version(entry))
            entry.setdefault("repository_suffix", repository_suffix(entry))
            entries.append(entry)

    return entries


def entry_arches(entry: dict) -> list[dict]:
    arches = entry.get("arches", DEFAULT_ARCHES)
    if not isinstance(arches, list) or not arches:
        raise MetadataError(
            f"{entry.get('path', '<unknown>')}: 'arches' must be a non-empty array"
        )

    normalized = []
    seen_platforms = set()
    for arch in arches:
        if not isinstance(arch, dict):
            raise MetadataError(
                f"{entry.get('path', '<unknown>')}: every arch must be an object"
            )
        platform = arch.get("platform")
        runner = arch.get("runner")
        if not isinstance(platform, str) or not platform:
            raise MetadataError(
                f"{entry.get('path', '<unknown>')}: arch.platform is required"
            )
        if not isinstance(runner, str) or not runner:
            raise MetadataError(
                f"{entry.get('path', '<unknown>')}: arch.runner is required"
            )
        if platform in seen_platforms:
            raise MetadataError(
                f"{entry.get('path', '<unknown>')}: duplicate platform '{platform}'"
            )
        seen_platforms.add(platform)
        artifact_arch = arch.get("artifact_arch") or platform.replace("/", "-").replace(
            "_", "-"
        )
        normalized.append(
            {
                "platform": platform,
                "runner": runner,
                "artifact_arch": artifact_arch,
            }
        )
    return normalized


def unique_list(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def replace_chip(value: str, source_chip: str, target_chip: str, field: str) -> str:
    marker = f"-{source_chip}-"
    replacement = f"-{target_chip}-"
    if marker not in value:
        raise MetadataError(
            f"{field}: cannot derive chip '{target_chip}' because '{value}' "
            f"does not contain '{marker}'"
        )
    return value.replace(marker, replacement, 1)


def expand_entry(entry: dict) -> list[dict]:
    source_chip = entry.get("chip")
    if not isinstance(source_chip, str) or not source_chip:
        return [copy.deepcopy(entry)]

    derived_chips = entry.get("derived_chips", [])
    if derived_chips is None:
        derived_chips = []
    if not isinstance(derived_chips, list):
        raise MetadataError(
            f"{entry.get('path', '<unknown>')}: derived_chips must be an array"
        )
    for chip in derived_chips:
        if not isinstance(chip, str) or not chip:
            raise MetadataError(
                f"{entry.get('path', '<unknown>')}: derived_chips contains an invalid chip"
            )

    chips = unique_list([source_chip, *derived_chips])
    expanded = []
    for chip in chips:
        derived = copy.deepcopy(entry)
        derived.pop("derived_chips", None)
        derived["chip"] = chip
        if chip != source_chip:
            derived["tags"] = [
                replace_chip(tag, source_chip, chip, "tags[]") for tag in entry["tags"]
            ]
            derived["base_image"] = replace_chip(
                entry["base_image"], source_chip, chip, "base_image"
            )
        expanded.append(derived)
    return expanded


def validate_entries(data: dict, root: Path, expand: bool = True) -> list[dict]:
    raw_entries = discover_entries(data, root)
    entries = []

    for index, entry in enumerate(raw_entries):
        if not isinstance(entry, dict):
            raise MetadataError(f"versions[{index}] must be an object")

        path = entry.get("path")
        if not isinstance(path, str) or not path:
            raise MetadataError(f"versions[{index}].path is required")
        if not path.startswith(f"{IMAGES_DIR}/"):
            raise MetadataError(f"{path}: path must start with '{IMAGES_DIR}/'")

        image_dir = root / path
        dockerfile = image_dir / "Dockerfile"
        if not dockerfile.is_file():
            raise MetadataError(f"{path}: Dockerfile not found")

        tags = entry.get("tags")
        if not isinstance(tags, list) or not tags:
            raise MetadataError(f"{path}: tags must be a non-empty array")
        for tag in tags:
            if not isinstance(tag, str) or not TAG_RE.match(tag):
                raise MetadataError(f"{path}: invalid image tag '{tag}'")

        image_version = entry_version(entry)
        if not isinstance(image_version, str) or not image_version:
            raise MetadataError(f"{path}: image_version is required for batch release")
        entry["image_version"] = image_version

        base_image = entry.get("base_image")
        if not isinstance(base_image, str) or not base_image:
            raise MetadataError(f"{path}: base_image is required")

        entry["arches"] = entry_arches(entry)
        if expand:
            entries.extend(expand_entry(entry))
        else:
            raw_entry = copy.deepcopy(entry)
            raw_entry.pop("derived_chips", None)
            entries.append(raw_entry)

    seen_tags: dict[tuple[str, str], str] = {}
    for entry in entries:
        path = entry["path"]
        suffix = repository_suffix(entry)
        for tag in entry["tags"]:
            if not isinstance(tag, str) or not TAG_RE.match(tag):
                raise MetadataError(f"{path}: invalid derived image tag '{tag}'")
            key = (suffix, tag)
            if key in seen_tags:
                raise MetadataError(
                    f"{path}: tag '{tag}' already used by {seen_tags[key]} "
                    f"for repository suffix '{suffix}'"
                )
            seen_tags[key] = path
    return entries


def metadata_entries(metadata_path: str, expand: bool = True) -> list[dict]:
    data = load_metadata(metadata_path)
    return validate_entries(data, repo_root(), expand=expand)


def select_entry(entries: list[dict], tag: str, image_key: str = "") -> dict:
    if image_key:
        key_matches = [
            entry
            for entry in entries
            if image_key in (entry_image_key(entry), entry["path"])
        ]
        if not key_matches:
            raise MetadataError(f"unknown image key '{image_key}'")
        for entry in key_matches:
            if tag in entry["tags"]:
                return entry
        raise MetadataError(f"{image_key}: tag '{tag}' is not defined for this image")

    matches = [entry for entry in entries if tag in entry["tags"]]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        available = ", ".join(entry_image_key(entry) for entry in matches)
        raise MetadataError(
            f"image tag '{tag}' is ambiguous. Specify --image-key. "
            f"Matching image keys: {available}"
        )
    available = ", ".join(entry["tags"][0] for entry in entries)
    raise MetadataError(f"unknown image tag '{tag}'. Available tags: {available}")


def parse_repositories(value: str) -> list[str]:
    repositories = []
    for item in re.split(r"[\s,]+", value.strip()):
        if item:
            if "://" in item or "@" in item:
                raise MetadataError(
                    "repository entries must not include URL schemes or credentials"
                )
            repositories.append(item.rstrip("/").lower())
    if not repositories:
        raise MetadataError("at least one image repository is required")
    return repositories


def categorized_repositories(repositories: list[str], entry: dict) -> list[str]:
    suffix = repository_suffix(entry).lower()
    image_platform = entry.get("image_platform", "").lower()
    result = []
    for repository in repositories:
        parts = repository.rsplit("/", 1)
        if len(parts) == 1:
            if repository == suffix:
                result.append(repository)
            elif image_platform and repository.startswith(f"{image_platform}-"):
                result.append(suffix)
            else:
                result.append(f"{repository}/{suffix}")
            continue

        namespace, name = parts
        if name == suffix:
            result.append(repository)
        elif image_platform and name.startswith(f"{image_platform}-"):
            result.append(f"{namespace}/{suffix}")
        else:
            result.append(f"{repository}/{suffix}")
    return unique_list(result)


def print_json(value: object) -> None:
    print(json.dumps(value, separators=(",", ":")))


def command_validate(args: argparse.Namespace) -> None:
    entries = metadata_entries(args.metadata)
    print(f"Validated {len(entries)} Image definition(s).")


def command_build_matrix(args: argparse.Namespace) -> None:
    include = []
    for entry in metadata_entries(args.metadata, expand=False):
        for arch in entry["arches"]:
            include.append(
                {
                    "image_tag": entry["tags"][0],
                    "image_key": entry_image_key(entry),
                    "repository_suffix": repository_suffix(entry),
                    "path": entry["path"],
                    "base_image": entry["base_image"],
                    "platform": arch["platform"],
                    "runner": arch["runner"],
                    "artifact_arch": arch["artifact_arch"],
                }
            )
    print_json({"include": include})


def command_publish_matrix(args: argparse.Namespace) -> None:
    entry = select_entry(
        metadata_entries(args.metadata), args.image_tag, args.image_key
    )
    include = []
    for arch in entry["arches"]:
        include.append(
            {
                "image_tag": entry["tags"][0],
                "image_key": entry_image_key(entry),
                "artifact_key": artifact_key(entry),
                "repository_suffix": repository_suffix(entry),
                "path": entry["path"],
                "base_image": entry["base_image"],
                "platform": arch["platform"],
                "runner": arch["runner"],
                "artifact_arch": arch["artifact_arch"],
            }
        )
    print_json({"include": include})


def command_batch_matrix(args: argparse.Namespace) -> None:
    include = [
        {
            "image_tag": entry["tags"][0],
            "image_key": entry_image_key(entry),
            "repository_suffix": repository_suffix(entry),
        }
        for entry in metadata_entries(args.metadata)
        if entry["image_version"] == args.image_version
    ]
    if not include:
        raise MetadataError(f"no image matches version '{args.image_version}'")
    print_json({"include": include})


def command_repositories(args: argparse.Namespace) -> None:
    repositories = parse_repositories(args.repositories)
    if args.image_tag:
        entry = select_entry(
            metadata_entries(args.metadata), args.image_tag, args.image_key
        )
        repositories = categorized_repositories(repositories, entry)
    if args.format == "json":
        print_json(repositories)
    else:
        print("\n".join(repositories))


def command_tags(args: argparse.Namespace) -> None:
    entry = select_entry(
        metadata_entries(args.metadata), args.image_tag, args.image_key
    )
    repositories = categorized_repositories(
        parse_repositories(args.repositories), entry
    )
    tags = []
    for repository in repositories:
        published_tags = []
        if args.include_base_tags or not args.tag_suffix:
            published_tags.extend(entry["tags"])
        if args.tag_suffix:
            published_tags.extend(f"{tag}{args.tag_suffix}" for tag in entry["tags"])
        if args.include_latest:
            published_tags.append("latest")

        for published_tag in unique_list(published_tags):
            if not TAG_RE.match(published_tag):
                raise MetadataError(f"invalid published image tag '{published_tag}'")
            tags.append(f"{repository}:{published_tag}")
    if args.format == "json":
        print_json(tags)
    else:
        print("\n".join(tags))


def command_path(args: argparse.Namespace) -> None:
    entry = select_entry(
        metadata_entries(args.metadata), args.image_tag, args.image_key
    )
    print(entry["path"])


def command_base_image(args: argparse.Namespace) -> None:
    entry = select_entry(
        metadata_entries(args.metadata), args.image_tag, args.image_key
    )
    print(entry["base_image"])


def command_artifact_key(args: argparse.Namespace) -> None:
    entry = select_entry(
        metadata_entries(args.metadata), args.image_tag, args.image_key
    )
    print(artifact_key(entry))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata", default=DEFAULT_METADATA, help="metadata JSON path"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate", help="validate metadata and Dockerfile paths"
    )
    validate.set_defaults(func=command_validate)

    build_matrix = subparsers.add_parser(
        "build-matrix", help="print full CI build matrix"
    )
    build_matrix.set_defaults(func=command_build_matrix)

    publish_matrix = subparsers.add_parser(
        "publish-matrix", help="print CI matrix for one tag"
    )
    publish_matrix.add_argument("--image-tag", required=True)
    publish_matrix.add_argument("--image-key", default="")
    publish_matrix.set_defaults(func=command_publish_matrix)

    batch_matrix = subparsers.add_parser(
        "batch-matrix", help="print reusable workflow matrix for a version"
    )
    batch_matrix.add_argument("--image-version", required=True)
    batch_matrix.set_defaults(func=command_batch_matrix)

    repositories = subparsers.add_parser(
        "repositories", help="normalize image repository list"
    )
    repositories.add_argument("--repositories", required=True)
    repositories.add_argument("--image-tag")
    repositories.add_argument("--image-key", default="")
    repositories.add_argument("--format", choices=("json", "newline"), default="json")
    repositories.set_defaults(func=command_repositories)

    tags = subparsers.add_parser(
        "tags", help="expand repositories and metadata aliases into full tags"
    )
    tags.add_argument("--image-tag", required=True)
    tags.add_argument("--image-key", default="")
    tags.add_argument("--repositories", required=True)
    tags.add_argument(
        "--tag-suffix", default="", help="suffix appended to every generated tag"
    )
    tags.add_argument(
        "--include-base-tags",
        action="store_true",
        help="include metadata tags without the suffix",
    )
    tags.add_argument(
        "--include-latest", action="store_true", help="include the latest tag"
    )
    tags.add_argument("--format", choices=("json", "newline"), default="json")
    tags.set_defaults(func=command_tags)

    path = subparsers.add_parser("path", help="print Dockerfile context path for a tag")
    path.add_argument("--image-tag", required=True)
    path.add_argument("--image-key", default="")
    path.set_defaults(func=command_path)

    base_image = subparsers.add_parser("base-image", help="print base image for a tag")
    base_image.add_argument("--image-tag", required=True)
    base_image.add_argument("--image-key", default="")
    base_image.set_defaults(func=command_base_image)

    artifact_key_parser = subparsers.add_parser(
        "artifact-key", help="print the digest artifact key for a tag"
    )
    artifact_key_parser.add_argument("--image-tag", required=True)
    artifact_key_parser.add_argument("--image-key", default="")
    artifact_key_parser.set_defaults(func=command_artifact_key)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except MetadataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
