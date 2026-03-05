from app.utils.approval import generate_approval_token, validate_approval_token


def test_validate_approval_token_accepts_valid_token():
    token = generate_approval_token("secret", "/infra/staging", 1000, "prod fix")
    assert validate_approval_token(
        secret="secret",
        directory="/infra/staging",
        requested_at_epoch=1000,
        reason="prod fix",
        provided_token=token,
        ttl_seconds=300,
        now_epoch=1200,
    )


def test_validate_approval_token_rejects_expired_token():
    token = generate_approval_token("secret", "/infra/staging", 1000, "prod fix")
    assert not validate_approval_token(
        secret="secret",
        directory="/infra/staging",
        requested_at_epoch=1000,
        reason="prod fix",
        provided_token=token,
        ttl_seconds=300,
        now_epoch=1301,
    )
