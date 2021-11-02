from __future__ import annotations

from typing import Optional, List, Dict, Union

from sqlalchemy import BigInteger, Column, Integer, String, UniqueConstraint

from database import database, session


class ImageHash(database.base):
    """Stored image hashes"""

    __tablename__ = "fun_dhash_images"

    idx = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger)
    channel_id = Column(BigInteger)
    message_id = Column(BigInteger)
    attachment_id = Column(BigInteger)
    hash = Column(String)

    @staticmethod
    def add(
        guild_id: int, channel_id: int, message_id: int, attachment_id: int, hash: str
    ) -> ImageHash:
        """Add new image hash"""
        image = ImageHash.get_by_attachment(
            guild_id=guild_id, attachment_id=attachment_id
        )
        if image is not None:
            return image

        image = ImageHash(
            guild_id=guild_id,
            channel_id=channel_id,
            message_id=message_id,
            attachment_id=attachment_id,
            hash=hash,
        )

        session.add(image)
        session.commit()

        return image

    @staticmethod
    def get_hash(guild_id: int, channel_id: int, hash: str):
        return (
            session.query(ImageHash)
            .filter_by(guild_id=guild_id, channel_id=channel_id, hash=hash)
            .all()
        )

    @staticmethod
    def get_by_channel(guild_id: int, channel_id: int):
        return (
            session.query(ImageHash)
            .filter_by(guild_id=guild_id, channel_id=channel_id)
            .all()
        )

    @staticmethod
    def get_by_message(guild_id: int, message_id: int):
        return (
            session.query(ImageHash)
            .filter_by(guild_id=guild_id, message_id=message_id)
            .all()
        )

    @staticmethod
    def get_by_attachment(guild_id: int, attachment_id: int):
        return (
            session.query(ImageHash)
            .filter_by(guild_id=guild_id, attachment_id=attachment_id)
            .one_or_none()
        )

    @staticmethod
    def delete_by_message(guild_id: int, message_id: int):
        image = (
            session.query(ImageHash)
            .filter_by(guild_id=guild_id, message_id=message_id)
            .delete()
        )
        session.commit()
        return image

    def __repr__(self) -> str:
        return (
            f'<{self.__class__.__name} idx="{self.idx}" guild_id="{self.guild_id}" '
            f'channel_id="{self.channel_id}" message_id="{self.message_id}" '
            f'attachement_id="{self.attachment_id}" hash="{self.hash}">'
        )

    def dump(self) -> dict:
        return {
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "message_id": self.message_id,
            "attachment_id": self.attachment_id,
            "hash": self.hash,
        }


class HashChannel(database.base):
    __tablename__ = "fun_dhash_channels"

    idx = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, nullable=False)
    channel_id = Column(BigInteger, nullable=False)
    reaction_limit = Column(Integer, nullable=False)

    __table_args__ = (UniqueConstraint(guild_id, channel_id),)

    @staticmethod
    def add(guild_id: int, channel_id: int, reaction_limit: int = 5) -> HashChannel:
        existing = HashChannel.get(guild_id, channel_id)

        if existing:
            return existing

        channel = HashChannel(
            guild_id=guild_id, channel_id=channel_id, reaction_limit=reaction_limit
        )
        session.add(channel)
        session.commit()
        return channel

    def set_limit(self, reaction_limit: int):
        self.reaction_limit = reaction_limit

        session.commit()

    @staticmethod
    def get(guild_id: int, channel_id: int) -> Optional[HashChannel]:
        query = (
            session.query(HashChannel)
            .filter_by(guild_id=guild_id, channel_id=channel_id)
            .one_or_none()
        )
        return query

    @staticmethod
    def get_all(guild_id: int) -> List[HashChannel]:
        query = session.query(HashChannel).filter_by(guild_id=guild_id).all()
        return query

    @staticmethod
    def remove(guild_id: int, channel_id: int):
        query = (
            session.query(HashChannel)
            .filter_by(guild_id=guild_id, channel_id=channel_id)
            .delete()
        )
        session.commit()
        return query

    def __repr__(self) -> str:
        return (
            f'<{self.__class__.__name__} idx="{self.idx}" '
            f'guild_id="{self.guild_id}" channel_id="{self.channel_id}">'
        )

    def dump(self) -> Dict[str, Union[int, str]]:
        return {
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
        }
