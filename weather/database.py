from __future__ import annotations

from typing import List, Optional

from sqlalchemy import BigInteger, Column, Integer, String

from pie.database import database, session


class Place(database.base):
    __tablename__ = "fun_weather_place"

    idx = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger)
    member_id = Column(BigInteger, default=None)
    name = Column(String)

    @staticmethod
    def set(guild_id: int, member_id: Optional[int], name: str) -> Place:
        place = Place.get(guild_id, member_id)
        if place is not None:
            place.name = name
        else:
            place = Place(
                guild_id=guild_id,
                member_id=member_id,
                name=name,
            )
        session.add(place)
        session.commit()
        return place

    @staticmethod
    def get(guild_id: int, member_id: Optional[int]) -> Optional[Place]:
        return (
            session.query(Place)
            .filter_by(guild_id=guild_id, member_id=member_id)
            .one_or_none()
        )

    @staticmethod
    def remove(guild_id: int, member_id: Optional[int]) -> int:
        query = (
            session.query(Place)
            .filter_by(guild_id=guild_id, member_id=member_id)
            .delete()
        )
        session.commit()
        return query

    @staticmethod
    def get_all(guild_id: int) -> List[Place]:
        return session.query(Place).filter_by(guild_id=guild_id).all()

    def __repr__(self) -> str:
        return (
            f"<Place idx='{self.idx}' guild_id='{self.guild_id}' "
            f"member_id='{self.member_id}' name='{self.name}'>"
        )

    def dump(self) -> dict:
        return {
            "guild_id": self.guild_id,
            "member_id": self.member_id,
            "name": self.name,
        }
