"""Quy ước DTO của VSF (giống Ralion): `dto/request/<tên>_request_dto.py` và `dto/response/<tên>_response_dto.py`."""

import ast
import re
from pathlib import Path

import pytest

DTO_ROOT = Path(__file__).resolve().parents[1] / "src" / "dto"


def _modules(kind: str) -> list[Path]:
    return sorted(path for path in (DTO_ROOT / kind).glob("*.py") if path.name != "__init__.py")


def _model_classes(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef) and any(getattr(base, "id", "") == "BaseModel" for base in node.bases)
    ]


def test_dto_folder_only_contains_request_and_response_packages() -> None:
    entries = {path.name for path in DTO_ROOT.iterdir() if path.name != "__pycache__"}
    assert entries == {"__init__.py", "request", "response"}


@pytest.mark.parametrize(("kind", "suffix"), [("request", "Request"), ("response", "Response")])
def test_module_and_class_names_follow_the_convention(kind: str, suffix: str) -> None:
    modules = _modules(kind)
    assert modules, f"chưa có DTO {kind} nào"
    for path in modules:
        assert path.name.endswith(f"_{kind}_dto.py"), f"{path.name} phải kết thúc bằng _{kind}_dto.py"
        for name in _model_classes(path):
            assert name.endswith(f"{suffix}DTO"), f"{path.name}: lớp {name} phải kết thúc bằng {suffix}DTO"


def test_routers_only_use_response_dtos_as_response_models() -> None:
    routers = Path(__file__).resolve().parents[1] / "src" / "api" / "routers"
    used = [
        name
        for path in routers.glob("*.py")
        for name in re.findall(r'response_model=(\w+)|"model": (\w+)', path.read_text(encoding="utf-8"))
        for name in name
        if name
    ]
    assert used, "chưa có router nào khai báo response_model"
    assert all(name.endswith("ResponseDTO") for name in used), used
