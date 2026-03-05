import anyio

from app.auth import StaticTokenVerifier


def test_static_token_verifier_accepts_known_token():
    verifier = StaticTokenVerifier(["token-1"], scopes=["mcp:read"])
    result = anyio.run(verifier.verify_token, "token-1")
    assert result is not None
    assert result.client_id == "static-client"
    assert "mcp:read" in result.scopes


def test_static_token_verifier_rejects_unknown_token():
    verifier = StaticTokenVerifier(["token-1"])
    result = anyio.run(verifier.verify_token, "wrong-token")
    assert result is None
