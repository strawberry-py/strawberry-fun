from __future__ import annotations

from typing import Tuple, Optional, List

from sqlalchemy import BigInteger, Column, Integer, String, func

from pie.database import database, session


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

    def get_given_top(
        guild_id: int, user_id: int, action: str, limit: int
    ) -> List[Relation]:
        """Get top given relations for given action."""
        query = (
            session.query(Relation)
            .filter_by(guild_id=guild_id, sender_id=user_id, action=action)
            .order_by(Relation.value.desc())
            .limit(limit)
            .all()
        )
        return query

    def get_received_top(
        guild_id: int, user_id: int, action: str, limit: int
    ) -> List[Relation]:
        """Get top received relations for given action."""
        query = (
            session.query(Relation)
            .filter_by(guild_id=guild_id, receiver_id=user_id, action=action)
            .order_by(Relation.value.desc())
            .limit(limit)
            .all()
        )
        return query

    def save(self):
        session.commit()

    def __repr__(self) -> str:
        return (
            f'<Relation guild_id="{self.guild_id}" '
            f'sender_id="{self.sender_id}" receiver_id="{self.receiver_id}" '
            f'action="{self.action}" value="{self.value}">'
        )

    def dump(self) -> dict:
        return {
            "guild_id": self.guild_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "action": self.action,
            "value": self.value,
        }


class RelationOverwrite(database.base):
    """Preferences of relation variants."""

    __tablename__ = "fun_fun_relation_variants"

    idx = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger)
    channel_id = Column(BigInteger)
    command = Column(String)
    variant = Column(String)

    @classmethod
    def set(cls, guild_id: int, channel_id: int, command: str, variant: str) -> bool:
        """Add variant. Entry will be deleted if variant is 'default'.

        :return: True if the entry was added or updated, False if it was deleted.
        """
        deleted = (
            session.query(cls)
            .filter_by(guild_id=guild_id, channel_id=channel_id, command=command)
            .delete()
        )

        if deleted == 1 and variant == "default":
            return False

        overwrite = cls(
            guild_id=guild_id, channel_id=channel_id, command=command, variant=variant
        )
        session.add(overwrite)
        session.commit()
        return True

    @classmethod
    def get(cls, guild_id: int, channel_id: int, command: str) -> Optional[str]:
        """Get variant."""
        return (
            session.query(cls)
            .filter_by(guild_id=guild_id, channel_id=channel_id, command=command)
            .one_or_none()
        )
