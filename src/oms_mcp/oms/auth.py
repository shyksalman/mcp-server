from typing import Any

from oms_mcp.exceptions import AuthenticationError


def _find_token(data: dict[str, Any], names: tuple[str, ...]) -> str | None:
    for name in names:
        value = data.get(name)
        if isinstance(value, str) and value:
            return value
    for nested in ("data", "tokens", "result"):
        value = data.get(nested)
        if isinstance(value, dict):
            token = _find_token(value, names)
            if token:
                return token
    return None


def extract_tokens(payload: Any) -> tuple[str, str | None]:
    """Keep OMS login response variations isolated here."""
    if not isinstance(payload, dict):
        raise AuthenticationError("OMS authentication response was invalid")
    access = _find_token(payload, ("access", "access_token", "accessToken", "token"))
    refresh = _find_token(payload, ("refresh", "refresh_token", "refreshToken"))
    if not access:
        raise AuthenticationError("OMS authentication response had no access token")
    return access, refresh
