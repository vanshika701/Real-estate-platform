from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(User.email == email))

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        full_name: str,
        role: UserRole,
        phone: str | None,
    ) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            phone=phone,
        )
        self.session.add(user)
        await self.session.flush()  # assigns user.id; the service owns the commit
        return user
