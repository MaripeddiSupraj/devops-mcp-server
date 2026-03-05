from app.tools import terraform_tools


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
