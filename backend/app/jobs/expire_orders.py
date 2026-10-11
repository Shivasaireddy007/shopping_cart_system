"""Cancel orders left unpaid for too long and release their stock.

    uv run python -m app.jobs.expire_orders

Run it every few minutes from a scheduler (cron, or a Kubernetes CronJob).
"""

import asyncio

from app.db import SessionLocal
from app.services.orders import expire_unpaid


async def main() -> None:
    async with SessionLocal() as session:
        print(f"Cancelled {await expire_unpaid(session)} unpaid order(s).")


if __name__ == "__main__":
    asyncio.run(main())
