from types import SimpleNamespace

from app.tools import terraform_tools


def test_validate_directory_rejects_when_roots_missing_and_unrestricted_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(
        terraform_tools,
        "settings",
        SimpleNamespace(terraform_allow_unrestricted=False, terraform_allowed_roots=[]),
    )

    assert terraform_tools._validate_directory(str(tmp_path)) is None


def test_validate_directory_allows_inside_configured_roots(tmp_path, monkeypatch):
    allowed_root = tmp_path / "infra"
    allowed_root.mkdir()
    tf_dir = allowed_root / "staging"
    tf_dir.mkdir()

    monkeypatch.setattr(
        terraform_tools,
        "settings",
        SimpleNamespace(terraform_allow_unrestricted=False, terraform_allowed_roots=[str(allowed_root)]),
    )

    assert terraform_tools._validate_directory(str(tf_dir)) == str(tf_dir.resolve())
