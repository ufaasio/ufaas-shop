import os

from usso import APIHeaderConfig, AuthConfig
from usso.integrations.fastapi import USSOAuthentication


def get_usso(raise_exception: bool = False) -> USSOAuthentication:
    base_usso_url = os.getenv("BASE_USSO_URL") or "https://usso.uln.me"

    usso = USSOAuthentication(
        jwt_config=AuthConfig(
            jwks_url=(f"{base_usso_url}/.well-known/jwks.json"),
            api_key_header=APIHeaderConfig(
                header_name="x-api-key",
                verify_endpoint=(f"{base_usso_url}/api/sso/v1/apikeys/verify"),
            ),
        ),
        from_base_usso_url=base_usso_url,
        raise_exception=raise_exception,
    )
    return usso
