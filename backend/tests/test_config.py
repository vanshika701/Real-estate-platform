import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cors_origins_accepts_comma_separated_string() -> None:
    settings = Settings(cors_origins="http://a.com, http://b.com")

    assert settings.cors_origins == ["http://a.com", "http://b.com"]


def test_production_rejects_default_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(app_env="production")


def test_production_accepts_custom_jwt_secret() -> None:
    settings = Settings(app_env="production", jwt_secret="a-real-secret")

    assert settings.jwt_secret == "a-real-secret"
