"""Tracks product changes so the cache and the search index follow them.

A SQLAlchemy session hook records every product created, updated or deleted in a flush.

- For search, it adds a `product.changed` outbox event in the same transaction; the relay
  sends it to Kafka and the search indexer consumes it. A rollback discards the event too.
- For the cache, the changes become "committed" only when the transaction commits; after
  the request, `publish` drops just those products' cached pages and retires cached listings.
"""

from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, UOWTransaction

from app.core.redis import get_redis
from app.events.outbox import PRODUCTS_TOPIC, add_event
from app.models import Product
from app.services.cache import CatalogCache

PENDING, COMMITTED, THIS_FLUSH = "products_pending", "products_committed", "products_this_flush"


def _slugs(product: Product) -> set[str]:
    """The current slug and, if it changed, the previous one (its cached page is stale too)."""
    history = inspect(product).attrs.slug.history
    return {s for s in [product.slug, *history.deleted] if s}


@event.listens_for(Session, "after_flush")
def _track(session: Session, _: UOWTransaction) -> None:
    pending: dict[int, set[str]] = session.info.setdefault(PENDING, {})
    this_flush: set[int] = session.info.setdefault(THIS_FLUSH, set())
    for obj in [*session.new, *session.dirty, *session.deleted]:
        if isinstance(obj, Product) and obj.id is not None:
            pending.setdefault(obj.id, set()).update(_slugs(obj))
            this_flush.add(obj.id)


@event.listens_for(Session, "after_flush_postexec")
def _write_outbox(session: Session, _: UOWTransaction) -> None:
    # Objects added here are flushed in the same flush, inside the same transaction.
    for product_id in sorted(session.info.pop(THIS_FLUSH, set())):
        add_event(session, PRODUCTS_TOPIC, str(product_id), "product.changed", {"product_id": product_id})


@event.listens_for(Session, "after_commit")
def _commit(session: Session) -> None:
    committed: dict[int, set[str]] = session.info.setdefault(COMMITTED, {})
    for product_id, slugs in session.info.pop(PENDING, {}).items():
        committed.setdefault(product_id, set()).update(slugs)


@event.listens_for(Session, "after_rollback")
def _rollback(session: Session) -> None:
    session.info.pop(PENDING, None)
    session.info.pop(THIS_FLUSH, None)


async def publish(session: AsyncSession, cache: CatalogCache | None = None) -> None:
    """Drops cached pages for products this session committed changes to, and retires listings."""
    changed: dict[int, set[str]] = session.info.pop(COMMITTED, {})
    if changed:
        await (cache or CatalogCache(get_redis())).invalidate(
            {s for slugs in changed.values() for s in slugs}
        )


def committed_ids(session: Any) -> set[int]:
    """For tests: products committed but not yet published."""
    return set(session.info.get(COMMITTED, {}))
