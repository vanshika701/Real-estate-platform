from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_check, str_enum

if TYPE_CHECKING:
    from app.models.listing import Listing


class UserRole(StrEnum):
    BUYER = "buyer"
    AGENT = "agent"


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (enum_check("role", UserRole),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[UserRole] = mapped_column(str_enum(UserRole))

    listings: Mapped[list["Listing"]] = relationship(back_populates="agent")
