from mcp.server.auth.provider import AccessToken, TokenVerifier


class StaticTokenVerifier(TokenVerifier):
    """
    Simple static bearer-token verifier for server-to-server deployments.
    Intended as a baseline guardrail for internal SSE/HTTP deployments.
    """

    def __init__(self, allowed_tokens: list[str], scopes: list[str] | None = None):
        self.allowed_tokens = {t.strip() for t in allowed_tokens if t and t.strip()}
        self.scopes = scopes or []

    async def verify_token(self, token: str) -> AccessToken | None:
        if token in self.allowed_tokens:
            return AccessToken(token=token, client_id="static-client", scopes=self.scopes)
        return None
