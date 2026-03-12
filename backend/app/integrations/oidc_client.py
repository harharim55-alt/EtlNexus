"""OIDC JWT validation client with JWKS caching and automatic key refresh.

Fetches the OpenID Connect well-known configuration on startup to discover
the JWKS endpoint, then caches the signing keys with a 6-hour TTL.  When a
JWT presents an unknown ``kid``, the cache is refreshed once before failing
so that key rotation is handled transparently.

Uses a persistent ``httpx.AsyncClient`` matching the pattern established by
``airflow_client.py``.
"""

import logging
import time

import httpx
import jwt as pyjwt
from jwt.exceptions import PyJWTError as JWTError

from app.config import settings

logger = logging.getLogger(__name__)

# JWKS cache TTL in seconds (6 hours)
_JWKS_TTL: float = 6 * 3600

# Roles accepted by the application — anything else is treated as "member".
VALID_ROLES: set[str] = {"admin", "member", "viewer"}


class OIDCClient:
    """Validates JWTs issued by the configured OIDC provider.

    Lifecycle:
        Call ``initialize()`` once at application startup (lifespan handler).
        Call ``close()`` during application shutdown.
    """

    def __init__(self) -> None:
        self._jwks: dict = {}
        self._jwks_fetched_at: float = 0.0
        self._well_known: dict = {}
        self._client: httpx.AsyncClient | None = None
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Startup / shutdown
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Fetch .well-known/openid-configuration and initial JWKS.

        Uses ``settings.sso_issuer_url`` (internal Docker URL) so that
        container-internal DNS resolves correctly at startup.
        """
        if not settings.sso_enabled:
            logger.info("SSO disabled — skipping OIDC client initialization")
            return

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            limits=httpx.Limits(
                max_connections=5,
                max_keepalive_connections=2,
                keepalive_expiry=30,
            ),
        )

        well_known_url = (
            f"{settings.sso_issuer_url.rstrip('/')}/.well-known/openid-configuration"
        )
        try:
            resp = await self._client.get(well_known_url)
            resp.raise_for_status()
            self._well_known = resp.json()
            logger.info("OIDC well-known configuration loaded from %s", well_known_url)
        except httpx.RequestError as exc:
            logger.warning("Could not reach OIDC well-known endpoint: %s", exc)
            return
        except httpx.HTTPStatusError as exc:
            logger.warning("OIDC well-known returned HTTP %s: %s", exc.response.status_code, exc)
            return

        await self._refresh_jwks()
        self._initialized = True

    async def close(self) -> None:
        """Close the underlying HTTP client. Call during application shutdown."""
        if self._client:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # JWKS management
    # ------------------------------------------------------------------

    async def _refresh_jwks(self) -> None:
        """Re-fetch JWKS from the provider.

        Called at startup, every 6 hours, or when an unknown ``kid`` is
        encountered during validation.
        """
        if not self._client:
            return

        jwks_uri = self._well_known.get("jwks_uri")
        if not jwks_uri:
            # Re-fetch well-known in case Keycloak wasn't ready at startup
            well_known_url = (
                f"{settings.sso_issuer_url.rstrip('/')}/.well-known/openid-configuration"
            )
            try:
                resp = await self._client.get(well_known_url)
                resp.raise_for_status()
                self._well_known = resp.json()
                jwks_uri = self._well_known.get("jwks_uri")
                if jwks_uri:
                    logger.info("OIDC well-known re-fetched successfully")
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                logger.warning("Failed to re-fetch OIDC well-known: %s", exc)

            if not jwks_uri:
                logger.warning("OIDC well-known configuration missing 'jwks_uri'")
                return

        try:
            resp = await self._client.get(jwks_uri)
            resp.raise_for_status()
            data = resp.json()
            # Index keys by kid for O(1) lookup
            self._jwks = {key["kid"]: key for key in data.get("keys", [])}
            self._jwks_fetched_at = time.monotonic()
            logger.debug("JWKS refreshed — %d keys cached", len(self._jwks))
        except (httpx.RequestError, httpx.HTTPStatusError, KeyError) as exc:
            logger.warning("Failed to refresh JWKS: %s", exc)

    def _is_jwks_stale(self) -> bool:
        """Return True if the JWKS cache has exceeded its TTL."""
        return (time.monotonic() - self._jwks_fetched_at) > _JWKS_TTL

    # ------------------------------------------------------------------
    # Token validation
    # ------------------------------------------------------------------

    async def validate_token(self, token: str) -> dict:
        """Decode and validate a JWT, returning its claims.

        Verification steps:
        - Signature verified against cached JWKS (RS256).
        - ``exp``, ``iss``, and ``aud`` claims are checked by the JWT library.
        - If the ``kid`` is not found in the cache a single JWKS refresh is
          attempted before raising.

        The issuer is accepted as either the internal Docker URL
        (``sso_issuer_url``) or the public-facing URL
        (``sso_public_issuer_url``) to handle tokens minted by Keycloak with
        the public hostname while the backend resolves via internal DNS.

        Args:
            token: Raw JWT string from the ``Authorization: Bearer`` header.

        Returns:
            Decoded claims dict.

        Raises:
            JWTError: When the token is invalid, expired, or has an
                unrecognised signature.
        """
        if not self._initialized:
            # Attempt late initialization in case Keycloak came up after startup
            logger.warning("OIDC client not initialized — attempting late initialization")
            await self.initialize()
            if not self._initialized:
                raise JWTError(
                    "OIDC client not initialized — Keycloak may be unreachable. "
                    "Check SSO_ISSUER_URL and Keycloak availability."
                )

        # Proactively refresh stale JWKS
        if self._is_jwks_stale():
            logger.info("JWKS cache stale (>%ds) — refreshing", int(_JWKS_TTL))
            await self._refresh_jwks()

        unverified_header = pyjwt.get_unverified_header(token)
        kid: str = unverified_header.get("kid", "")

        signing_key = self._get_signing_key(kid)
        if signing_key is None:
            # Attempt a one-shot async refresh on cache miss (key rotation).
            await self._refresh_jwks()
            signing_key = self._get_signing_key(kid)
            if signing_key is None:
                raise JWTError(f"Unknown signing key kid='{kid}'")

        # Accept both internal and public issuer URLs
        valid_issuers = [settings.sso_issuer_url.rstrip("/")]
        if settings.sso_public_issuer_url:
            valid_issuers.append(settings.sso_public_issuer_url.rstrip("/"))

        # Keycloak access tokens carry the client ID in "azp" rather than
        # "aud" (which only appears in id_tokens).  Decode without strict aud
        # verification, then validate azp/aud manually.
        last_exc: Exception = JWTError("Token validation failed")
        for issuer in valid_issuers:
            try:
                claims = pyjwt.decode(
                    token,
                    signing_key,
                    algorithms=["RS256"],
                    issuer=issuer,
                    options={"verify_aud": False},
                )
                # Validate audience: accept either aud or azp matching the config
                expected = settings.sso_audience
                if expected:
                    aud = claims.get("aud")
                    azp = claims.get("azp", "")
                    aud_ok = (
                        aud == expected
                        or (isinstance(aud, list) and expected in aud)
                        or azp == expected
                    )
                    if not aud_ok:
                        raise JWTError(
                            f"Token audience/azp does not match '{expected}'"
                        )
                return claims
            except JWTError as exc:
                last_exc = exc

        raise last_exc

    def _get_signing_key(self, kid: str) -> pyjwt.PyJWK | None:
        """Find a JWK by its ``kid`` in the cached JWKS and return a PyJWK key.

        Args:
            kid: Key ID from the JWT header.

        Returns:
            A ``PyJWK`` instance if found, otherwise ``None``.
        """
        jwk_data = self._jwks.get(kid)
        if jwk_data is None:
            return None
        return pyjwt.PyJWK(jwk_data)

    # ------------------------------------------------------------------
    # Claims extraction helpers
    # ------------------------------------------------------------------

    def extract_groups(self, claims: dict) -> list[str]:
        """Extract group names from JWT claims.

        Reads the claim path defined by ``settings.sso_groups_claim``
        (e.g. ``"groups"``).  Handles both flat string lists and
        Keycloak-style path strings that start with ``"/"``
        (``"/Dagger"`` → ``"Dagger"``).

        Args:
            claims: Decoded JWT claims dict.

        Returns:
            List of normalised group name strings.
        """
        raw: list[str] = claims.get(settings.sso_groups_claim, [])
        if not isinstance(raw, list):
            raw = [raw] if raw else []
        return [g.lstrip("/") for g in raw if isinstance(g, str)]

    def extract_role(self, claims: dict) -> str:
        """Extract the user's primary role from JWT claims.

        Supports both flat claim keys (``"role"``) and nested dot-separated
        paths (``"realm_access.roles"``).  When the resolved value is a list
        the first element whose value matches ``settings.sso_admin_role`` is
        returned first; otherwise the first element is used.  Defaults to
        ``"member"`` when the claim is absent or empty.

        Args:
            claims: Decoded JWT claims dict.

        Returns:
            Role string, e.g. ``"admin"`` or ``"member"``.
        """
        path_parts = settings.sso_role_claim.split(".")
        value: object = claims
        try:
            for part in path_parts:
                if not isinstance(value, dict):
                    return "member"
                value = value[part]
        except (KeyError, TypeError):
            return "member"

        if isinstance(value, list):
            roles: list[str] = [r for r in value if isinstance(r, str)]
            if settings.sso_admin_role in roles and settings.sso_admin_role in VALID_ROLES:
                return settings.sso_admin_role
            for r in roles:
                if r in VALID_ROLES:
                    return r
            return "member"

        if isinstance(value, str):
            return value if value in VALID_ROLES else "member"

        return "member"


# Module-level singleton — import this in auth.py and lifespan hooks.
oidc_client = OIDCClient()
