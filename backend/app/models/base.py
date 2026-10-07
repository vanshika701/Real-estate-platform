from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Deterministic constraint names so Alembic can reliably alter or drop them later.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def str_enum(enum_cls: type[StrEnum]) -> Enum:
    """Store enums as VARCHAR (paired with enum_check) instead of a native Postgres ENUM.

    Native ENUM types need special migration handling to add or rename values;
    a CHECK constraint is a plain ALTER and still rejects invalid values at the DB level.
    """
    return Enum(
        enum_cls,
        native_enum=False,
        create_constraint=False,  # declared explicitly via enum_check so it gets a stable name
        length=32,
        values_callable=lambda e: [member.value for member in e],
    )


def enum_check(column: str, enum_cls: type[StrEnum]) -> CheckConstraint:
    values = ", ".join(f"'{member.value}'" for member in enum_cls)
    return CheckConstraint(f"{column} IN ({values})", name=f"{column}_valid")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
