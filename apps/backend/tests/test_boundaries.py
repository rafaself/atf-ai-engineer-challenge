import ast
import os
import subprocess
import sys
from pathlib import Path


def test_contracts_and_application_import_without_provider_modules(
    tmp_path: Path,
) -> None:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("AWS_")
    }
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import sys, importlib, pkgutil; "
            "packages = [importlib.import_module('emporio_music_backend.' + name) "
            "for name in ('contracts', 'ports', 'application')]; "
            "[importlib.import_module(module.name) for package in packages "
            "for module in pkgutil.walk_packages(package.__path__, package.__name__ + '.')]; "
            "assert not {'fastapi', 'boto3', 'botocore', 'pydantic_ai', 'sqlite3'} & sys.modules.keys()",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )


def test_core_dependencies_point_inward() -> None:
    root = Path(__file__).parents[1] / "src" / "emporio_music_backend"
    allowed = {
        "contracts": {"contracts"},
        "ports": {"contracts", "ports"},
        "application": {"contracts", "ports", "application"},
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
                    if module.startswith("emporio_music_backend."):
                        assert module.split(".")[1] in permitted, path
                    assert module.split(".")[0] not in {
                        "fastapi",
                        "boto3",
                        "botocore",
                        "pydantic_ai",
                        "sqlite3",
                    }, path


def test_package_initializers_have_no_implementations_or_barrel_imports() -> None:
    root = Path(__file__).parents[1] / "src" / "emporio_music_backend"
    barrels = {
        f"emporio_music_backend.{name}"
        for name in ("contracts", "ports", "application")
    }
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
