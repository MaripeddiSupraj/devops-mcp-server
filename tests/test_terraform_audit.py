from app.tools import terraform_tools
from app.utils.approval import generate_approval_token
import time


def test_terraform_apply_logs_rejected_for_non_auto_approve(tmp_path, monkeypatch):
    tf_dir = tmp_path / "infra"
    tf_dir.mkdir()

    monkeypatch.setattr(terraform_tools, "_validate_directory", lambda directory: str(tf_dir))

    events = []
    monkeypatch.setattr(terraform_tools, "audit_event", lambda action, status, details=None: events.append((action, status)))

    result = terraform_tools.terraform_apply(str(tf_dir), auto_approve=False)

    assert result["status"] == "error"
    assert ("terraform_apply", "attempted") in events
    assert ("terraform_apply", "rejected") in events


def test_terraform_apply_rejects_without_approval_fields(tmp_path, monkeypatch):
    tf_dir = tmp_path / "infra"
    tf_dir.mkdir()
    monkeypatch.setattr(terraform_tools, "_validate_directory", lambda directory: str(tf_dir))
    monkeypatch.setattr(
        terraform_tools,
        "settings",
        type(
            "Settings",
            (),
            {
                "terraform_apply_require_approval": True,
                "terraform_apply_approval_secret": "secret",
                "terraform_apply_token_ttl_seconds": 300,
            },
        )(),
    )

    result = terraform_tools.terraform_apply(str(tf_dir), auto_approve=True)
    assert result["status"] == "error"
    assert "approval_reason" in result["message"]


def test_terraform_apply_allows_valid_approval_token(tmp_path, monkeypatch):
    tf_dir = tmp_path / "infra"
    tf_dir.mkdir()
    monkeypatch.setattr(terraform_tools, "_validate_directory", lambda directory: str(tf_dir))
    monkeypatch.setattr(terraform_tools, "run_command", lambda cmd, cwd=None: "ok")
    monkeypatch.setattr(
        terraform_tools,
        "settings",
        type(
            "Settings",
            (),
            {
                "terraform_apply_require_approval": True,
                "terraform_apply_approval_secret": "secret",
                "terraform_apply_token_ttl_seconds": 300,
            },
        )(),
    )
    requested_at = int(time.time())
    reason = "hotfix"
    token = generate_approval_token("secret", str(tf_dir), requested_at, reason)

    result = terraform_tools.terraform_apply(
        str(tf_dir),
        auto_approve=True,
        approval_reason=reason,
        approval_requested_at_epoch=requested_at,
        approval_token=token,
    )

    assert result["status"] == "success"
