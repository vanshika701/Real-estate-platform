import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cors_origins_accepts_comma_separated_string() -> None:
    settings = Settings(cors_origins="http://a.com, http://b.com")

    assert settings.cors_origins == ["http://a.com", "http://b.com"]


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (
            "postgres://u:p@db.example.com:5432/app",
            "postgresql+asyncpg://u:p@db.example.com:5432/app",
        ),
        ("postgresql://u:p@db.example.com/app", "postgresql+asyncpg://u:p@db.example.com/app"),
        ("postgresql://u:p@h/app?sslmode=require", "postgresql+asyncpg://u:p@h/app?ssl=require"),
        ("postgresql+asyncpg://u:p@h/app", "postgresql+asyncpg://u:p@h/app"),
    ],
)
def test_database_url_is_normalised_for_asyncpg(given: str, expected: str) -> None:
    assert Settings(database_url=given).database_url == expected


def test_production_rejects_default_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(app_env="production")


def test_production_accepts_custom_jwt_secret() -> None:
    settings = Settings(app_env="production", jwt_secret="a-real-secret")

    assert settings.jwt_secret == "a-real-secret"
