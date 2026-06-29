#!/usr/bin/env python3
"""Helpers for ModelArts image metadata used by local scripts and CI."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


DEFAULT_METADATA = "modelarts_publish_version.json"
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


def entry_arches(entry: dict) -> list[dict]:
    arches = entry.get("arches", DEFAULT_ARCHES)
    if not isinstance(arches, list) or not arches:
        raise MetadataError(f"{entry.get('path', '<unknown>')}: 'arches' must be a non-empty array")

    normalized = []
    seen_platforms = set()
    for arch in arches:
        if not isinstance(arch, dict):
            raise MetadataError(f"{entry.get('path', '<unknown>')}: every arch must be an object")
        platform = arch.get("platform")
        runner = arch.get("runner")
        if not isinstance(platform, str) or not platform:
            raise MetadataError(f"{entry.get('path', '<unknown>')}: arch.platform is required")
        if not isinstance(runner, str) or not runner:
            raise MetadataError(f"{entry.get('path', '<unknown>')}: arch.runner is required")
        if platform in seen_platforms:
            raise MetadataError(f"{entry.get('path', '<unknown>')}: duplicate platform '{platform}'")
        seen_platforms.add(platform)
        artifact_arch = arch.get("artifact_arch") or platform.replace("/", "-").replace("_", "-")
        normalized.append(
            {
                "platform": platform,
                "runner": runner,
                "artifact_arch": artifact_arch,
            }
        )
    return normalized


def validate_entries(data: dict, root: Path) -> list[dict]:
    entries = data["versions"]
    seen_tags: dict[str, str] = {}
    seen_paths = set()

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise MetadataError(f"versions[{index}] must be an object")

        path = entry.get("path")
        if not isinstance(path, str) or not path:
            raise MetadataError(f"versions[{index}].path is required")
        if not path.startswith("modelarts/"):
            raise MetadataError(f"{path}: path must start with 'modelarts/'")
        if path in seen_paths:
            raise MetadataError(f"{path}: duplicate path")
        seen_paths.add(path)

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
            if tag in seen_tags:
                raise MetadataError(f"{path}: tag '{tag}' already used by {seen_tags[tag]}")
            seen_tags[tag] = path

        modelarts_version = entry.get("modelarts_version")
        if not isinstance(modelarts_version, str) or not modelarts_version:
            raise MetadataError(f"{path}: modelarts_version is required for batch release")

        entry["arches"] = entry_arches(entry)

    return entries


def metadata_entries(metadata_path: str) -> list[dict]:
    data = load_metadata(metadata_path)
    return validate_entries(data, repo_root())


def select_entry(entries: list[dict], tag: str) -> dict:
    for entry in entries:
        if tag in entry["tags"]:
            return entry
    available = ", ".join(entry["tags"][0] for entry in entries)
    raise MetadataError(f"unknown ModelArts tag '{tag}'. Available tags: {available}")


def parse_repositories(value: str) -> list[str]:
    repositories = []
    for item in re.split(r"[\s,]+", value.strip()):
        if item:
            repositories.append(item.rstrip("/"))
    if not repositories:
        raise MetadataError("at least one image repository is required")
    return repositories


def print_json(value: object) -> None:
    print(json.dumps(value, separators=(",", ":")))


def command_validate(args: argparse.Namespace) -> None:
    entries = metadata_entries(args.metadata)
    print(f"Validated {len(entries)} ModelArts image definition(s).")


def command_build_matrix(args: argparse.Namespace) -> None:
    include = []
    for entry in metadata_entries(args.metadata):
        for arch in entry["arches"]:
            include.append(
                {
                    "modelarts_tag": entry["tags"][0],
                    "path": entry["path"],
                    "platform": arch["platform"],
                    "runner": arch["runner"],
                    "artifact_arch": arch["artifact_arch"],
                }
            )
    print_json({"include": include})


def command_publish_matrix(args: argparse.Namespace) -> None:
    entry = select_entry(metadata_entries(args.metadata), args.modelarts_tag)
    include = []
    for arch in entry["arches"]:
        include.append(
            {
                "modelarts_tag": entry["tags"][0],
                "path": entry["path"],
                "platform": arch["platform"],
                "runner": arch["runner"],
                "artifact_arch": arch["artifact_arch"],
            }
        )
    print_json({"include": include})


def command_batch_matrix(args: argparse.Namespace) -> None:
    tags = [
        entry["tags"][0]
        for entry in metadata_entries(args.metadata)
        if entry["modelarts_version"] == args.modelarts_version
    ]
    if not tags:
        raise MetadataError(f"no ModelArts image matches version '{args.modelarts_version}'")
    print_json({"modelarts_tag": tags})


def command_repositories(args: argparse.Namespace) -> None:
    repositories = parse_repositories(args.repositories)
    if args.format == "json":
        print_json(repositories)
    else:
        print("\n".join(repositories))


def command_tags(args: argparse.Namespace) -> None:
    entry = select_entry(metadata_entries(args.metadata), args.modelarts_tag)
    repositories = parse_repositories(args.repositories)
    tags = [f"{repository}:{tag}" for repository in repositories for tag in entry["tags"]]
    if args.format == "json":
        print_json(tags)
    else:
        print("\n".join(tags))


def command_path(args: argparse.Namespace) -> None:
    entry = select_entry(metadata_entries(args.metadata), args.modelarts_tag)
    print(entry["path"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", default=DEFAULT_METADATA, help="metadata JSON path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate metadata and Dockerfile paths")
    validate.set_defaults(func=command_validate)

    build_matrix = subparsers.add_parser("build-matrix", help="print full CI build matrix")
    build_matrix.set_defaults(func=command_build_matrix)

    publish_matrix = subparsers.add_parser("publish-matrix", help="print CI matrix for one tag")
    publish_matrix.add_argument("--modelarts-tag", required=True)
    publish_matrix.set_defaults(func=command_publish_matrix)

    batch_matrix = subparsers.add_parser("batch-matrix", help="print reusable workflow matrix for a version")
    batch_matrix.add_argument("--modelarts-version", required=True)
    batch_matrix.set_defaults(func=command_batch_matrix)

    repositories = subparsers.add_parser("repositories", help="normalize image repository list")
    repositories.add_argument("--repositories", required=True)
    repositories.add_argument("--format", choices=("json", "newline"), default="json")
    repositories.set_defaults(func=command_repositories)

    tags = subparsers.add_parser("tags", help="expand repositories and metadata aliases into full tags")
    tags.add_argument("--modelarts-tag", required=True)
    tags.add_argument("--repositories", required=True)
    tags.add_argument("--format", choices=("json", "newline"), default="json")
    tags.set_defaults(func=command_tags)

    path = subparsers.add_parser("path", help="print Dockerfile context path for a tag")
    path.add_argument("--modelarts-tag", required=True)
    path.set_defaults(func=command_path)

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
