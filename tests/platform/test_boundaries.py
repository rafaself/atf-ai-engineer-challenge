import ast
import os
import subprocess
import sys
import tomllib
from pathlib import Path

from tests._support import REPOSITORY_ROOT


def test_contracts_and_application_import_without_provider_modules(
    tmp_path: Path,
) -> None:
    package_source = REPOSITORY_ROOT / "packages/emporio_music/src"
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("AWS_")
    }
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import sys, importlib, pkgutil; sys.path.insert(0, sys.argv[1]); "
            "packages = [importlib.import_module('emporio_music.' + name) "
            "for name in ('domain', 'ports', 'application')]; "
            "[importlib.import_module(module.name) for package in packages "
            "for module in pkgutil.walk_packages(package.__path__, package.__name__ + '.')]; "
            "assert not {'fastapi', 'boto3', 'botocore', 'pydantic_ai', 'sqlite3'} & sys.modules.keys()",
            str(package_source),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )


def test_core_dependencies_point_inward() -> None:
    root = REPOSITORY_ROOT / "packages/emporio_music/src/emporio_music"
    allowed = {
        "domain": {"domain"},
        "ports": {"domain", "ports"},
        "application": {"domain", "ports", "application"},
    }
    for layer, permitted in allowed.items():
        for path in (root / layer).rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                modules: list[str] = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    assert node.level == 0, (
                        "Use explicit imports for visible boundaries"
                    )
                    modules = [node.module or ""]
                for module in modules:
                    if module.startswith("emporio_music."):
                        assert module.split(".")[1] in permitted, path
                    assert module.split(".")[0] not in {
                        "fastapi",
                        "boto3",
                        "botocore",
                        "pydantic_ai",
                        "sqlite3",
                    }, path


def test_package_initializers_have_no_implementations_or_barrel_imports() -> None:
    root = REPOSITORY_ROOT / "packages/emporio_music/src/emporio_music"
    barrels = {f"emporio_music.{name}" for name in ("domain", "ports", "application")}
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text())
        if path.name == "__init__.py":
            assert all(
                isinstance(node, (ast.Import, ast.ImportFrom))
                or (
                    isinstance(node, ast.Expr)
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                )
                or (
                    isinstance(node, ast.Assign)
                    and all(
                        isinstance(target, ast.Name) and target.id == "__all__"
                        for target in node.targets
                    )
                )
                for node in tree.body
            ), path
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module not in barrels, (path, node.module)


def test_apps_depend_on_the_shared_package_without_cross_imports() -> None:
    repository_root = REPOSITORY_ROOT
    project_files = {
        "api": repository_root / "apps/api/pyproject.toml",
        "cli": repository_root / "apps/cli/pyproject.toml",
    }
    source_roots = {
        "api": repository_root / "apps/api/src",
        "cli": repository_root / "apps/cli/src",
    }
    for app, project_file in project_files.items():
        project = tomllib.loads(project_file.read_text())["project"]
        assert any(
            dependency.startswith("emporio-music")
            for dependency in project["dependencies"]
        )
        other_app = "cli" if app == "api" else "api"
        forbidden_namespace = f"emporio_music_{other_app}"
        for path in source_roots[app].rglob("*.py"):
            tree = ast.parse(path.read_text())
            imported_modules = [
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            ]
            imported_modules.extend(
                node.module or ""
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            )
            assert all(
                module.split(".")[0] != forbidden_namespace
                for module in imported_modules
            ), path

    shared_project = tomllib.loads(
        (repository_root / "packages/emporio_music/pyproject.toml").read_text()
    )["project"]
    assert not any(
        dependency.startswith(("emporio-music-api", "emporio-music-cli"))
        for dependency in shared_project["dependencies"]
    )
    shared_source = repository_root / "packages/emporio_music/src/emporio_music"
    for path in shared_source.rglob("*.py"):
        tree = ast.parse(path.read_text())
        imported_modules = [
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        ]
        imported_modules.extend(
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        assert all(
            module.split(".")[0] not in {"emporio_music_api", "emporio_music_cli"}
            for module in imported_modules
        ), path
