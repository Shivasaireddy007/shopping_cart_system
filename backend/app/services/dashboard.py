"""Admin dashboard figures. Days are counted in India time, not UTC."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import ColumnElement, Date, cast, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.models import Order, OrderStatus, Payment, Product
from app.schemas.orders import DashboardOut, DayRevenue, HotProduct, StockAlert
from app.services.cache import CatalogCache

IST = ZoneInfo("Asia/Kolkata")
LOW_STOCK_BELOW = 5


def _ist_day(column: ColumnElement[datetime] | InstrumentedAttribute[datetime | None]) -> ColumnElement[date]:
    # A literal (not a bound parameter), so SELECT and GROUP BY render the identical expression.
    return cast(func.timezone(literal_column("'Asia/Kolkata'"), column), Date)


async def build(session: AsyncSession, cache: CatalogCache, now: datetime | None = None) -> DashboardOut:
    today = (now or datetime.now(UTC)).astimezone(IST).date()
    week = [today - timedelta(days=d) for d in range(6, -1, -1)]

    paid_day = _ist_day(Order.paid_at)
    paid = (
        await session.execute(
            select(paid_day, func.sum(Order.total), func.count(Order.id))
            .where(Order.paid_at.is_not(None), paid_day >= week[0])
            .group_by(paid_day)
        )
    ).all()
    by_day: dict[date, tuple[int, int]] = {row[0]: (int(row[1]), int(row[2])) for row in paid}

    orders_today = await session.scalar(
        select(func.count(Order.id)).where(_ist_day(Order.created_at) == today)
    )
    to_ship = await session.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.paid))
    failed_today = await session.scalar(
        select(func.count(Payment.id)).where(
            Payment.status == "failed", _ist_day(Payment.created_at) == today
        )
    )
    low_stock = await session.scalars(
        select(Product)
        .where(Product.is_active.is_(True), Product.stock < LOW_STOCK_BELOW)
        .order_by(Product.stock, Product.id)
        .limit(6)
    )

    hot: list[HotProduct] = []
    if top := await cache.top_products(5):
        names = dict(
            (await session.execute(select(Product.id, Product.name).where(Product.id.in_(top)))).all()
        )
        scores = await cache.view_counts(top)
        hot = [HotProduct(id=i, name=names[i], views=scores.get(i, 0)) for i in top if i in names]

    return DashboardOut(
        orders_today=orders_today or 0,
        revenue_today=by_day.get(today, (0, 0))[0],
        to_ship=to_ship or 0,
        failed_payments_today=failed_today or 0,
        revenue_by_day=[
            DayRevenue(date=d.isoformat(), revenue=by_day.get(d, (0, 0))[0], orders=by_day.get(d, (0, 0))[1])
            for d in week
        ],
        low_stock=[StockAlert(id=p.id, name=p.name, sku=p.sku, stock=p.stock) for p in low_stock],
        hot_products=hot,
    )
