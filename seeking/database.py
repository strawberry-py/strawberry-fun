from __future__ import annotations

from typing import List, Optional

from sqlalchemy import BigInteger, Column, Integer, String

from database import database, session


class Seeking(database.base):
    __tablename__ = "fun_seeking_seeking"

    idx = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger)
    channel_id = Column(BigInteger, default=None)
    message_id = Column(BigInteger, unique=True)
    user_id = Column(BigInteger)
    text = Column(String)

    @staticmethod
    def add(
        guild_id: int, channel_id: int, message_id: int, user_id: int, text: str
    ) -> "Seeking":
        query = Seeking(
            guild_id=guild_id,
            channel_id=channel_id,
            message_id=message_id,
            user_id=user_id,
            text=text,
        )
        session.add(query)
        session.commit()
        return query

    @staticmethod
    def get(guild_id: int, channel_id: int, item_id: int) -> Optional[Seeking]:
        return (
            session.query(Seeking)
            .filter_by(guild_id=guild_id, channel_id=channel_id, idx=item_id)
            .one_or_none()
        )

    @staticmethod
    def remove(guild_id: int, channel_id: int, item_id: int) -> int:
        query = (
            session.query(Seeking)
            .filter_by(guild_id=guild_id, channel_id=channel_id, idx=item_id)
            .delete()
        )
        session.commit()
        return query

    @staticmethod
    def count_all(guild_id=guild_id, channel_id=channel_id) -> int:
        _ = (
            session.query(Seeking)
            .filter_by(guild_id=guild_id, channel_id=channel_id)
            .count()
        )

    @staticmethod
    def get_all(guild_id: int, channel_id: int = None) -> List[Seeking]:
        if not channel_id:
            return session.query(Seeking).filter_by(guild_id=guild_id).all()
        return (
            session.query(Seeking)
            .filter_by(guild_id=guild_id, channel_id=channel_id)
            .all()
        )

    def __repr__(self) -> str:
        return (
            f"<Seeking idx='{self.idx}' guild_id='{self.guild_id}' "
            f"channel_id='{self.channel_id}' message_id='{self.message_id}' "
            f"user_id='{self.user_id}' text='{self.text}'>"
        )

    def dump(self) -> dict:
        return {
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "message_id": self.message_id,
            "user_id": self.user_id,
            "text": self.text,
        }
