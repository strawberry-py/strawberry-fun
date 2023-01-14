from __future__ import annotations

from typing import Optional

from sqlalchemy import Column, BigInteger, String

from pie.database import database, session


class Details(database.base):
    """User-agent and cf_clearance cookie for weeb module"""

    __tablename__ = "fun_weeb_connection_details"

    guild_id = Column(BigInteger, primary_key=True)
    user_agent = Column(String)
    cf_clearance = Column(String)

    @staticmethod
    def set(guild_id: int, user_agent: str, cf_clearance: str) -> Details:
        """Add or update connection values."""
        details = Details.get(guild_id)
        if details is not None:
            details.user_agent = user_agent
            details.cf_clearance = cf_clearance
        else:
            details = Details(
                guild_id=guild_id,
                user_agent=user_agent,
                cf_clearance=cf_clearance,
            )
        session.add(details)
        session.commit()
        return details

    @staticmethod
    def get(guild_id: int) -> Optional[Details]:
        """Get connection details in supplied guild."""
        return session.query(Details).filter_by(guild_id=guild_id).one_or_none()

    @staticmethod
    def remove(guild_id: int) -> int:
        """Remove connection details in supplied guild."""
        details = session.query(Details).filter_by(guild_id=guild_id).delete()
        session.commit()
        return details
