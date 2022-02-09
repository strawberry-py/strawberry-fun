from __future__ import annotations

import enum
from typing import Dict, List, Optional, Union

from sqlalchemy import BigInteger, Boolean, Column, Enum, Integer, String
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from pie.database import database, session


class MacroMatch(enum.Enum):
    FULL = 0
    START = 1
    END = 2
    ANY = 3


class TextMacro(database.base):
    __tablename__ = "fun_macro_text"

    idx = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger)
    name = Column(String)
    triggers = relationship(lambda: TextMacroTrigger, cascade="all, delete")
    responses = relationship(lambda: TextMacroResponse, cascade="all, delete")
    dm = Column(Boolean)
    delete_trigger = Column(Boolean)
    sensitive = Column(Boolean)
    match = Column(Enum(MacroMatch))
    channels = relationship(lambda: TextMacroChannel, cascade="all, delete")
    users = relationship(lambda: TextMacroUser, cascade="all, delete")
    counter = Column(Integer, default=0)

    @staticmethod
    def add(
        guild_id: int,
        name: str,
        triggers: List[str],
        responses: List[str],
        dm: bool,
        delete_trigger: bool,
        sensitive: bool,
        match: MacroMatch,
        channels: List[int],
        users: List[int],
    ) -> TextMacro:
        if TextMacro.get(guild_id, name):
            raise ValueError(f"TextMacro '{name}' already exists.")

        macro = TextMacro(
            guild_id=guild_id,
            name=name,
            triggers=[TextMacroTrigger(text=t) for t in triggers],
            responses=[TextMacroResponse(text=r) for r in responses],
            dm=dm,
            delete_trigger=delete_trigger,
            match=match,
            channels=[TextMacroChannel(channel_id=c) for c in channels]
            if channels
            else [],
            users=[TextMacroUser(user_id=u) for u in users] if users else [],
        )
        session.add(macro)
        session.commit()
        return macro

    def update(
        self,
        *,
        triggers: Optional[List[str]] = None,
        responses: Optional[List[str]] = None,
        dm: Optional[bool] = None,
        delete_trigger: Optional[bool] = None,
        sensitive: Optional[bool] = None,
        match: Optional[MacroMatch] = None,
        channels: Optional[List[int]] = None,
        users: Optional[List[int]] = None,
    ):
        if triggers is not None:
            self.triggers = [TextMacroTrigger(text=t) for t in triggers]
        if responses is not None:
            self.responses = [TextMacroResponse(text=r) for r in responses]
        if dm is not None:
            self.dm = dm
        if delete_trigger is not None:
            self.delete_trigger = delete_trigger
        if sensitive is not None:
            self.sensitive = sensitive
        if match is not None:
            self.match = match
        if channels is not None:
            self.channels = (
                [TextMacroChannel(channel_id=c) for c in channels] if channels else []
            )
        if users is not None:
            self.users = [TextMacroUser(user_id=u) for u in users] if users else []

        session.commit()

    @staticmethod
    def get(guild_id: int, name: str) -> Optional[TextMacro]:
        query = (
            session.query(TextMacro)
            .filter_by(guild_id=guild_id, name=name)
            .one_or_none()
        )
        return query

    @staticmethod
    def get_all(guild_id: Optional[int]) -> List[TextMacro]:
        query = session.query(TextMacro)
        if guild_id is not None:
            query = query.filter_by(guild_id=guild_id)
        query = query.all()
        return query

    @staticmethod
    def remove(guild_id: int, name: str) -> int:
        query = (
            session.query(TextMacro)
            .filter_by(
                guild_id=guild_id,
                name=name,
            )
            .delete()
        )
        session.commit()
        return query

    def bump(self):
        self.counter += 1
        session.commit()

    def save(self):
        session.commit()

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            + " ".join(f"{k}='{v}'" for k, v in self.dump().items())
            + ">"
        )

    def dump(self) -> dict:
        return {
            "guild_id": self.guild_id,
            "name": self.name,
            "triggers": [s.text for s in self.triggers],
            "responses": [s.text for s in self.responses],
            "dm": self.dm,
            "delete_trigger": self.delete_trigger,
            "sensitive": self.sensitive,
            "match": self.match.name,
            "channels": [c.channel_id for c in self.channels],
            "users": [u.user_id for u in self.users],
            "counter": self.counter,
        }


class TextMacroTrigger(database.base):
    __tablename__ = "fun_macro_text_triggers"

    idx = Column(Integer, primary_key=True, autoincrement=True)
    macro_idx = Column(Integer, ForeignKey("fun_macro_text.idx", ondelete="CASCADE"))
    text = Column(String)

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"macro_idx='{self.macro_idx} text='{self.text}'>"
        )

    def __str__(self) -> str:
        return self.name

    def dump(self) -> Dict[str, Union[str, int]]:
        return {
            "macro_idx": self.macro_idx,
            "text": self.text,
        }


class TextMacroResponse(database.base):
    __tablename__ = "fun_macro_text_responses"

    idx = Column(Integer, primary_key=True, autoincrement=True)
    macro_idx = Column(Integer, ForeignKey("fun_macro_text.idx", ondelete="CASCADE"))
    text = Column(String)

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"macro_idx='{self.macro_idx} text='{self.text}'>"
        )

    def __str__(self) -> str:
        return self.name

    def dump(self) -> Dict[str, Union[str, int]]:
        return {
            "macro_idx": self.macro_idx,
            "text": self.text,
        }


class TextMacroChannel(database.base):
    __tablename__ = "fun_macro_text_channels"

    idx = Column(Integer, primary_key=True, autoincrement=True)
    macro_idx = Column(Integer, ForeignKey("fun_macro_text.idx", ondelete="CASCADE"))
    channel_id = Column(BigInteger)

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"macro_idx='{self.macro_idx}' channel_id='{self.channel_id}'>"
        )

    def dump(self) -> Dict[str, int]:
        return {
            "macro_idx": self.macro_idx,
            "channel_id": self.macro_idx,
        }


class TextMacroUser(database.base):
    __tablename__ = "fun_macro_text_users"

    idx = Column(Integer, primary_key=True, autoincrement=True)
    macro_idx = Column(Integer, ForeignKey("fun_macro_text.idx", ondelete="CASCADE"))
    user_id = Column(BigInteger)

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"macro_idx='{self.macro_idx}' user_id='{self.user_id}'>"
        )

    def dump(self) -> Dict[str, int]:
        return {
            "macro_idx": self.macro_idx,
            "channel_id": self.macro_idx,
        }
