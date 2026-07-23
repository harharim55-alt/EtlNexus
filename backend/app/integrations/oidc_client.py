"""OIDC JWT validation client with JWKS caching and automatic key refresh.

Fetches the OpenID Connect well-known configuration on startup to discover
the JWKS endpoint, then caches the signing keys with a 6-hour TTL.  When a
JWT presents an unknown ``kid``, the cache is refreshed once before failing
so that key rotation is handled transparently.

Uses a persistent ``httpx.AsyncClient`` matching the pattern used by the other
integration clients.
"""

import logging
import time
from urllib.parse import urlparse, urlunparse

import httpx
import jwt as pyjwt
from jwt.exceptions import PyJWTError as JWTError

from app.config import settings

logger = logging.getLogger(__name__)

# JWKS cache TTL in seconds (default 6 hours; override via JWKS_CACHE_TTL_SECONDS)
_JWKS_TTL: float = settings.jwks_cache_ttl_seconds

# Minimum interval between on-demand JWKS refreshes triggered by unknown kid
_ON_DEMAND_REFRESH_COOLDOWN: float = 30.0


def _resolve_verify() -> bool | str:
    """Resolve the httpx ``verify`` value from the OIDC TLS settings.

    ``OIDC_VERIFY_SSL=false`` disables verification entirely and **ignores**
    ``OIDC_CA_BUNDLE`` (so a stale/missing bundle path can never raise
    ``FileNotFoundError`` when the user only meant to skip verification).
    When verification is on, a non-empty ``OIDC_CA_BUNDLE`` is used as the
    trust store (private/internal CA); otherwise the system/certifi CAs.

    Returns:
        ``False`` to skip verification, a CA bundle path string, or ``True``.
    """
    if not settings.oidc_verify_ssl:
        return False
    if settings.oidc_ca_bundle:
        return settings.oidc_ca_bundle
    return True


class OIDCClient:
    """Validates JWTs issued by the configured OIDC provider.

    Lifecycle:
        Call ``initialize()`` once at application startup (lifespan handler).
        Call ``close()`` during application shutdown.
    """

    def __init__(self) -> None:
        self._jwks: dict = {}
        self._jwks_fetched_at: float = 0.0
        self._last_on_demand_refresh_at: float = 0.0
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
            verify=_resolve_verify(),
            timeout=httpx.Timeout(settings.oidc_http_timeout_seconds),
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

        # Rewrite jwks_uri to use the internal Docker hostname so the
        # backend can always fetch keys regardless of KC_HOSTNAME setting.
        internal = urlparse(settings.sso_issuer_url)
        parsed = urlparse(jwks_uri)
        if parsed.netloc != internal.netloc:
            jwks_uri = urlunparse(parsed._replace(scheme=internal.scheme, netloc=internal.netloc))
            logger.debug("Rewrote JWKS URI to internal: %s", jwks_uri)

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

        Verification (matching the reference Keycloak + FastAPI pattern):
        - Signature verified against the cached JWKS (RS256).
        - ``exp`` is checked. **Audience and issuer are not enforced** — many
          IdPs mint an ``aud`` of ``account`` and carry the client id only in
          ``azp``, and the issuer host can differ from what the backend reaches,
          so enforcing them causes false 401s. Trust comes from the JWKS
          signature.
        - If the ``kid`` is not found in the cache, a single rate-limited JWKS
          refresh is attempted before raising (handles key rotation).

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
            # Rate-limited on-demand refresh on cache miss (key rotation).
            now = time.monotonic()
            if (now - self._last_on_demand_refresh_at) >= _ON_DEMAND_REFRESH_COOLDOWN:
                await self._refresh_jwks()
                self._last_on_demand_refresh_at = now
            signing_key = self._get_signing_key(kid)
            if signing_key is None:
                raise JWTError(f"Unknown signing key kid='{kid}'")

        # Verify signature + expiry only. Audience/issuer are intentionally not
        # enforced (see docstring) to interoperate with varied Keycloak configs.
        return pyjwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

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
        """Extract group names from JWT claims, applying the SSO→team rename map.

        Reads the claim path defined by ``settings.sso_groups_claim``
        (e.g. ``"groups"``).  Handles both flat string lists and
        Keycloak-style path strings that start with ``"/"``
        (``"/Dagger"`` → ``"Dagger"``).

        Group handling depends on ``settings.sso_group_map``:
        - **Non-empty** → the map is an **allow-list + rename**: only groups whose
          raw value or ``"/"``-stripped form is a key are kept (renamed to the
          value); every other group is dropped and never becomes a team.
        - **Empty** → all groups pass through as their ``"/"``-stripped name.

        Args:
            claims: Decoded JWT claims dict.

        Returns:
            List of normalised (and renamed) team name strings.
        """
        raw: list[str] = claims.get(settings.sso_groups_claim, [])
        if not isinstance(raw, list):
            raw = [raw] if raw else []

        group_map = settings.sso_group_map or {}
        result: list[str] = []
        for g in raw:
            if not isinstance(g, str):
                continue
            stripped = g.lstrip("/")
            if group_map:
                mapped = group_map.get(g) or group_map.get(stripped)
                if mapped is None:
                    continue  # not in the map → not a recognised team, drop it
                result.append(mapped)
            else:
                result.append(stripped)
        return result


# Module-level singleton — import this in auth.py and lifespan hooks.
oidc_client = OIDCClient()
