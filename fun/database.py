from __future__ import annotations

from typing import Tuple, Optional

from sqlalchemy import BigInteger, Column, Integer, String, func

from database import database, session


class Relation(database.base):
    """User relations are based on using hug, pet, whip, ..."""

    __tablename__ = "fun_fun_relations"

    idx = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger)
    sender_id = Column(BigInteger)
    receiver_id = Column(BigInteger, nullable=True)
    action = Column(String)
    value = Column(Integer)

    @staticmethod
    def add(guild_id: int, sender_id: int, receiver_id: int, action: str) -> Relation:
        """Add new relation.

        :return: Relation.
        """

        relation = Relation.get(guild_id, sender_id, receiver_id, action)

        if not relation:
            relation = Relation(
                guild_id=guild_id,
                sender_id=sender_id,
                receiver_id=receiver_id,
                action=action,
                value=0,
            )

        relation.value += 1

        session.merge(relation)
        session.commit()

        return relation

    @staticmethod
    def get(
        guild_id: int, sender_id: int, receiver_id: int, action: str
    ) -> Optional[Relation]:
        """Get relation if exists.

        :return: Optional[Relation]
        """

        query = (
            session.query(Relation)
            .filter_by(
                guild_id=guild_id,
                sender_id=sender_id,
                receiver_id=receiver_id,
                action=action,
            )
            .one_or_none()
        )

        return query

    def get_user_relation(guild_id: int, user_id: int, action: str) -> Tuple[int, int]:
        gave = (
            session.query(func.sum(Relation.value))
            .filter_by(guild_id=guild_id, sender_id=user_id, action=action)
            .group_by(Relation.sender_id)
            .scalar()
            or 0
        )

        got = (
            session.query(func.sum(Relation.value))
            .filter_by(guild_id=guild_id, receiver_id=user_id, action=action)
            .group_by(Relation.receiver_id)
            .scalar()
            or 0
        )

        return gave, got

    def save(self):
        session.commit()

    def __repr__(self) -> str:
        return (
            f'<Relation idx="{self.idx}" guild_id="{self.guild_id}" '
            f'sender_id="{self.sender_id}" receiver_id="{self.receiver_id}" action="{self.action}">'
        )

    def dump(self) -> dict:
        return {
            "guild_id": self.guild_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "action": self.action,
        }
