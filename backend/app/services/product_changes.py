"""Tracks committed product changes so caches and the search index can follow them.

A SQLAlchemy session hook records every product created, updated or deleted in a flush;
the records only become "committed" when the transaction commits, and are dropped on
rollback. After a request (or job), `publish` invalidates the cache and re-indexes just
those products, so a checkout that rolls back never touches the cache or the index.
"""

import logging
from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, UOWTransaction

from app.core.config import get_settings
from app.core.redis import get_redis
from app.models import Product
from app.services.cache import CatalogCache
from app.services.search import index
from app.services.search.client import SearchClient, get_search_client

log = logging.getLogger(__name__)

PENDING, COMMITTED = "products_pending", "products_committed"


def _slugs(product: Product) -> set[str]:
    """The current slug and, if it changed, the previous one (its cached page is stale too)."""
    history = inspect(product).attrs.slug.history
    return {s for s in [product.slug, *history.deleted] if s}


@event.listens_for(Session, "after_flush")
def _track(session: Session, _: UOWTransaction) -> None:
    pending: dict[int, set[str]] = session.info.setdefault(PENDING, {})
    for obj in [*session.new, *session.dirty, *session.deleted]:
        if isinstance(obj, Product) and obj.id is not None:
            pending.setdefault(obj.id, set()).update(_slugs(obj))


@event.listens_for(Session, "after_commit")
def _commit(session: Session) -> None:
    committed: dict[int, set[str]] = session.info.setdefault(COMMITTED, {})
    for product_id, slugs in session.info.pop(PENDING, {}).items():
        committed.setdefault(product_id, set()).update(slugs)


@event.listens_for(Session, "after_rollback")
def _rollback(session: Session) -> None:
    session.info.pop(PENDING, None)


async def publish(
    session: AsyncSession, cache: CatalogCache | None = None, search: SearchClient | None = None
) -> None:
    """Invalidates cached pages and re-indexes the products this session committed changes to."""
    changed: dict[int, set[str]] = session.info.pop(COMMITTED, {})
    if not changed:
        return

    await (cache or CatalogCache(get_redis())).invalidate({s for slugs in changed.values() for s in slugs})

    if get_settings().search_enabled:
        try:
            await index.sync(search or get_search_client(), session, list(changed))
        except Exception:
            # The nightly or on-demand rebuild repairs anything missed here.
            log.exception("Search sync failed for products %s", sorted(changed))


def committed_ids(session: Any) -> set[int]:
    """For tests: products committed but not yet published."""
    return set(session.info.get(COMMITTED, {}))
