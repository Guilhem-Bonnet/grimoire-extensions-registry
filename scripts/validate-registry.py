#!/usr/bin/env python3
"""CI de conformité du registry d'extensions Grimoire.

Vérifie l'index, les checksums des archives, le manifeste contenu dans
chaque archive, la cohérence hooks/permissions et, si un export catalogue
est fourni, l'existence des patterns déclarés.

Autonome : la validation structurelle du manifeste est embarquée (miroir du
contrat de ``grimoire.tools.ext_manager`` dans grimoire-kit, qui reste la
source de vérité du format). Seule dépendance optionnelle : jsonschema.

Usage:
    python3 scripts/validate-registry.py --registry . [--catalogue export.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tarfile
import tempfile
from pathlib import Path

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$")
PATTERN_ID_RE = re.compile(r"^(ORG|ORC|GOV|QUA|KNO|RUN|COG|MOD)-\d{2}$")

REQUIRED_KEYS = (
    "manifestVersion", "id", "name", "version", "description", "license",
    "authors", "compat", "provides", "patterns", "permissions", "install",
)
STEP_KINDS = ("copy", "script", "pip", "npm")
FILESYSTEM_PERMS = ("none", "artifacts", "workspace")
MEMORY_PERMS = ("none", "read", "readwrite")


def is_safe_relpath(value: str) -> bool:
    if not value or value.startswith(("/", "\\")):
        return False
    return ".." not in Path(value).parts


def validate_manifest(manifest: dict, ext_dir: Path) -> list[str]:
    """Validation structurelle du manifeste (miroir du contrat grimoire-kit)."""
    errors: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in manifest:
            errors.append(f"champ requis manquant : {key}")
    if errors:
        return errors

    if manifest["manifestVersion"] != 1:
        errors.append("manifestVersion non supporté (attendu : 1)")
    if not ID_RE.match(str(manifest["id"])):
        errors.append(f"id invalide : {manifest['id']}")
    if not SEMVER_RE.match(str(manifest["version"])):
        errors.append(f"version non semver : {manifest['version']}")
    if not manifest["authors"]:
        errors.append("authors vide")

    implements = manifest["patterns"].get("implements", [])
    if not implements:
        errors.append("patterns.implements vide (mapping catalogue obligatoire)")
    errors.extend(
        f"pattern id invalide : {pid}"
        for pid in [*implements, *manifest["patterns"].get("requires", [])]
        if not PATTERN_ID_RE.match(str(pid))
    )

    perms = manifest["permissions"]
    if perms.get("filesystem") not in FILESYSTEM_PERMS:
        errors.append(f"permissions.filesystem invalide : {perms.get('filesystem')}")
    if perms.get("memory") not in MEMORY_PERMS:
        errors.append(f"permissions.memory invalide : {perms.get('memory')}")
    if not isinstance(perms.get("network"), bool):
        errors.append("permissions.network doit être booléen")

    for kind, paths in manifest["provides"].items():
        if kind == "nodes":
            continue
        for rel in paths:
            if not is_safe_relpath(rel):
                errors.append(f"provides.{kind} : chemin non sûr : {rel}")
            elif not (ext_dir / rel).exists():
                errors.append(f"provides.{kind} : fichier absent : {rel}")

    steps = manifest["install"].get("steps", [])
    if not steps:
        errors.append("install.steps vide")
    for i, step in enumerate(steps):
        kind = step.get("kind")
        if kind not in STEP_KINDS:
            errors.append(f"step {i} : kind invalide : {kind}")
        elif kind == "copy":
            if not is_safe_relpath(step.get("from", "")):
                errors.append(f"step {i} : from non sûr : {step.get('from')}")
            elif not (ext_dir / step["from"]).exists():
                errors.append(f"step {i} : source absente : {step['from']}")
            if not is_safe_relpath(step.get("to", "")):
                errors.append(f"step {i} : to non sûr : {step.get('to')}")
        elif kind == "script":
            if not is_safe_relpath(step.get("path", "")):
                errors.append(f"step {i} : path non sûr : {step.get('path')}")
            elif not (ext_dir / step["path"]).is_file():
                errors.append(f"step {i} : script absent : {step['path']}")
        elif not step.get("packages"):
            errors.append(f"step {i} : packages vide")

    verify = manifest["install"].get("verify")
    if verify and not (ext_dir / verify).is_file():
        errors.append(f"install.verify : script absent : {verify}")
    return errors


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def check_release(
    registry: Path, ext_id: str, release: dict, catalogue_patterns: set[str] | None
) -> list[str]:
    errors: list[str] = []
    ref = f"{ext_id}@{release['version']}"
    archive = registry / release["archive"]
    if not archive.is_file():
        return [f"{ref} : archive absente ({release['archive']})"]
    if sha256(archive) != release["checksum"]:
        return [f"{ref} : checksum invalide"]

    with tempfile.TemporaryDirectory(prefix="registry-ci-") as tmp:
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar.getmembers():
                if not is_safe_relpath(member.name):
                    return [f"{ref} : membre d'archive non sûr : {member.name}"]
            tar.extractall(tmp, filter="data")
        ext_dir = Path(tmp)
        manifest_path = ext_dir / "extension.json"
        if not manifest_path.is_file():
            return [f"{ref} : extension.json absent de l'archive"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        errors.extend(f"{ref} : {e}" for e in validate_manifest(manifest, ext_dir))
        if manifest.get("id") != ext_id:
            errors.append(f"{ref} : id du manifeste ({manifest.get('id')}) != index")
        if manifest.get("version") != release["version"]:
            errors.append(f"{ref} : version du manifeste != index")
        if manifest.get("provides", {}).get("hooks") and not manifest.get(
            "permissions", {}
        ).get("hooks"):
            errors.append(f"{ref} : hooks fournis mais permissions.hooks vide")
        if catalogue_patterns is not None:
            errors.extend(
                f"{ref} : pattern inconnu du catalogue : {pid}"
                for pid in manifest.get("patterns", {}).get("implements", [])
                if pid not in catalogue_patterns
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validation du registry d'extensions")
    parser.add_argument("--registry", type=Path, default=Path(__file__).parents[1])
    parser.add_argument("--catalogue", type=Path, default=None)
    args = parser.parse_args()

    registry = args.registry.resolve()
    index_path = registry / "registry.json"
    if not index_path.is_file():
        print(f"ERREUR : {index_path} introuvable", file=sys.stderr)
        return 1
    index = json.loads(index_path.read_text(encoding="utf-8"))

    try:
        import jsonschema

        schema = json.loads(
            (registry / "registry.schema.json").read_text(encoding="utf-8")
        )
        jsonschema.validate(index, schema)
        print("OK : index conforme au schéma")
    except ImportError:
        print("INFO : jsonschema absent, validation du schéma d'index sautée")

    catalogue_patterns = None
    if args.catalogue:
        catalogue = json.loads(args.catalogue.read_text(encoding="utf-8"))
        catalogue_patterns = {p["id"] for p in catalogue["patterns"]}
        print(f"OK : catalogue chargé ({len(catalogue_patterns)} patterns)")

    errors: list[str] = []
    releases = 0
    for ext_id, entry in sorted(index.get("extensions", {}).items()):
        versions = {r["version"] for r in entry["versions"]}
        if entry["latest"] not in versions:
            errors.append(f"{ext_id} : latest ({entry['latest']}) absent des versions")
        for release in entry["versions"]:
            releases += 1
            errors.extend(check_release(registry, ext_id, release, catalogue_patterns))

    if errors:
        for error in errors:
            print(f"ERREUR : {error}", file=sys.stderr)
        return 1
    print(
        f"OK : {releases} release(s) de "
        f"{len(index.get('extensions', {}))} extension(s) conformes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
