from __future__ import annotations

import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Column, DateTime, Integer, String

from database import database, session


class Relation(database.base):
    """Relation.
    Handles all relations between users.
    """

    __tablename__ = "fun_meme_relations"

    idx = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger)
    sender_id = Column(BigInteger)
    receiver_id = Column(BigInteger, nullable=True)
    action = Column(String)

    @staticmethod
    def add(guild_id: int, sender_id: int, receiver_id: int, action: str) -> Relation:
        """Add new relation.

        :return: Relation.
        """
        relation = Relation(
            guild_id=guild_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            action=action
        )

        session.add(relation)
        session.commit()

        return relation
        
    def get_user_relation(guild_id: int, user_id: int, action: str) -> Tuple[int, int]:
        
        gave = session.query(Relation).filter_by(
                    guild_id=guild_id,
                    sender_id=user_id,
                    action=action
                ).count()
            
        got = session.query(Relation).filter_by(
                    guild_id=guild_id,
                    receiver_id=user_id,
                    action=action
                ).count()
        
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
            'receiver_id': self.receiver_id,
            "action": self.action
        }

