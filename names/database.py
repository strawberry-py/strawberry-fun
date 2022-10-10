from __future__ import annotations

from typing import Optional

from sqlalchemy import Column, Integer, BigInteger

from pie.database import database, session


class Price(database.base):
    """Prices for nickname subcommands"""

    __tablename__ = "fun_names_prices"

    guild_id = Column(BigInteger, primary_key=True)
    set_price = Column(Integer)
    reset_price = Column(Integer)

    @staticmethod
    def set(guild_id: int, set_price: int, reset_price: int) -> Price:
        """Add or update prices."""
        price = Price.get(guild_id)
        if price is not None:
            price.set_price = set_price
            price.reset_price = reset_price
        else:
            price = Price(
                guild_id=guild_id,
                set_price=set_price,
                reset_price=reset_price,
            )
        session.add(price)
        session.commit()
        return price

    @staticmethod
    def get(guild_id: int) -> Optional[Price]:
        """Get prices in supplied guild."""
        return session.query(Price).filter_by(guild_id=guild_id).one_or_none()

    @staticmethod
    def remove(guild_id: int) -> int:
        """Remove prices in supplied guild."""
        price = session.query(Price).filter_by(guild_id=guild_id).delete()
        session.commit()
        return price
