"""SQLAlchemy models — ``Base.metadata`` is the Alembic autogenerate target.

Every model class MUST be imported here so that importing ``app.models`` (which
``alembic/env.py`` does transitively via ``Base``) registers all 17 tables on
``Base.metadata``. Missing an import here = a table silently absent from autogenerate.

17 tables: the 16 TZ §13 tables + the ``topics`` lookup (orchestrator directive 1).
"""

from app.models.analytics import AppEvent, GenerationLog
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.billing import Payment, Product, Subscription, UserLimits
from app.models.card import Card
from app.models.deck import Deck, DeckCard, DeckSpreadCompatibility
from app.models.prompt import PromptTemplate
from app.models.reading import Reading, ReadingCard
from app.models.spread import SpreadPosition, SpreadType
from app.models.topic import Topic
from app.models.user import User

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    # 17 models
    "Topic",
    "User",
    "Deck",
    "DeckCard",
    "DeckSpreadCompatibility",
    "Card",
    "SpreadType",
    "SpreadPosition",
    "Reading",
    "ReadingCard",
    "PromptTemplate",
    "UserLimits",
    "Product",
    "Payment",
    "Subscription",
    "AppEvent",
    "GenerationLog",
]
