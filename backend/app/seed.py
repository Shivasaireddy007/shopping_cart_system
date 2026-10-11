"""Seed a demo catalog, logins and (optionally) sample order history.

    uv run python -m app.seed --products 1000 --orders 60

Safe to run repeatedly: it only adds products when the catalog is empty, and only adds
sample orders when there are none.
"""

import argparse
import asyncio
import random
import secrets
from datetime import UTC, datetime, timedelta

from faker import Faker
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.core.text import slugify, unique_slug
from app.db import SessionLocal
from app.models import Category, Order, OrderItem, OrderStatus, Payment, Product, User
from app.services.shipping import shipping_fee

CATEGORIES = [
    "Running Shoes", "Sneakers", "Formal Shoes", "Sandals", "Boots", "T-Shirts", "Shirts", "Jeans",
    "Trousers", "Shorts", "Jackets", "Hoodies", "Track Pants", "Kurtas", "Watches", "Backpacks",
]  # fmt: skip
BRANDS = ["Nike", "Adidas", "Puma", "Reebok", "Bata", "Woodland", "Campus", "Sparx"]
MODEL_WORDS = [
    "Air",
    "Flex",
    "Street",
    "Urban",
    "Trail",
    "Classic",
    "Swift",
    "Cloud",
    "Velocity",
    "Core",
    "Pro",
    "Lite",
]
MODEL_SUFFIXES = ["", " 2", " 3", " Max", " Plus", " Elite", " Prime"]
COLORS = ["black", "white", "red", "blue", "green", "grey"]
SIZES = ["S", "M", "L", "XL"]

DEMO_USERS = [
    ("demo@example.com", "Demo Customer", False),
    ("admin@example.com", "Demo Admin", True),
]
DEMO_PASSWORD = "demo-password"


async def seed(product_count: int, order_count: int = 0) -> None:
    fake = Faker("en_IN")
    async with SessionLocal() as session:
        for email, name, is_admin in DEMO_USERS:
            if not await session.scalar(select(User.id).where(User.email == email)):
                session.add(
                    User(
                        email=email, name=name, password_hash=hash_password(DEMO_PASSWORD), is_admin=is_admin
                    )
                )

        categories = []
        for name in CATEGORIES:
            category = await session.scalar(select(Category).where(Category.slug == slugify(name)))
            if category is None:
                category = Category(name=name, slug=slugify(name))
                session.add(category)
            categories.append(category)
        await session.flush()

        if await session.scalar(select(func.count(Product.id))):
            print("Catalog already has products, skipping.")
        else:
            for _ in range(product_count):
                category = random.choice(categories)
                brand = random.choice(BRANDS)
                model = " ".join(random.sample(MODEL_WORDS, 2)) + random.choice(MODEL_SUFFIXES)
                name = f"{brand} {model} {category.name}"
                price = random.randint(199, 9999) * 100
                color, size = random.choice(COLORS), random.choice(SIZES)
                session.add(
                    Product(
                        category_id=category.id,
                        sku=f"{brand[:3].upper()}-{fake.unique.bothify('######')}",
                        name=name,
                        slug=unique_slug(name),
                        description=(
                            f"{model} from {brand} in {color}. Built for everyday wear with a comfortable "
                            f"fit and durable materials. Size {size}."
                        ),
                        brand=brand,
                        price=price,
                        # Whole rupees, never below the price.
                        mrp=round(price * random.choice([1, 1.1, 1.25, 1.5]) / 100) * 100,
                        stock=random.choice([0, *range(1, 200)]),
                        weight_grams=random.randint(100, 2000),
                        attributes={"color": color, "size": size},
                    )
                )
            print(f"Seeded {product_count} products.")

        await session.commit()

        if order_count and not await session.scalar(select(func.count(Order.id))):
            await _seed_orders(session, order_count)
            await session.commit()
            print(f"Seeded {order_count} sample orders over the last 14 days.")
    print(f"Logins: {', '.join(email for email, _, _ in DEMO_USERS)} / {DEMO_PASSWORD}")


async def _seed_orders(session: AsyncSession, count: int) -> None:
    """Backdated sample orders for the demo customer, so the dashboard and history have data."""
    customer = await session.scalar(select(User).where(User.email == DEMO_USERS[0][0]))
    products = (await session.scalars(select(Product).where(Product.is_active.is_(True)).limit(300))).all()
    assert customer is not None and products
    now = datetime.now(UTC)
    address = {
        "name": "Asha Rao", "phone": "9876543210", "line1": "12, 4th Cross, MG Road", "line2": None,
        "city": "Bengaluru", "state": "Karnataka", "pincode": "560001",
    }  # fmt: skip

    for _ in range(count):
        placed = now - timedelta(
            days=random.randint(0, 13), hours=random.randint(0, 23), minutes=random.randint(0, 59)
        )
        lines = [
            OrderItem(
                product_id=p.id,
                sku=p.sku,
                name=p.name,
                unit_price=p.price,
                quantity=q,
                line_total=p.price * q,
                weight_grams=p.weight_grams,
            )
            for p, q in (
                (random.choice(products), random.choice([1, 1, 1, 2])) for _ in range(random.randint(1, 3))
            )
        ]
        subtotal = sum(line.line_total for line in lines)
        fee = shipping_fee(subtotal)
        status = random.choices(
            [OrderStatus.delivered, OrderStatus.shipped, OrderStatus.paid, OrderStatus.cancelled],
            [5, 3, 2, 1],
        )[0]
        paid = status != OrderStatus.cancelled
        order = Order(
            number=f"ORD-{placed:%Y%m%d}-{secrets.token_hex(3).upper()}",
            user_id=customer.id,
            status=status,
            subtotal=subtotal,
            shipping_fee=fee,
            total=subtotal + fee,
            shipping_address=address,
            razorpay_order_id=f"order_demo{secrets.token_hex(6)}",
            paid_at=placed + timedelta(minutes=2) if paid else None,
            cancelled_at=placed + timedelta(minutes=30) if not paid else None,
            created_at=placed,
            items=lines,
        )
        session.add(order)
        await session.flush()
        if paid:
            session.add(
                Payment(
                    order_id=order.id,
                    razorpay_payment_id=f"pay_demo{secrets.token_hex(6)}",
                    amount=order.total,
                    status="captured",
                    method=random.choice(["upi", "upi", "card", "netbanking"]),
                )
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--products", type=int, default=1000)
    parser.add_argument("--orders", type=int, default=0, help="sample orders over the last 14 days")
    args = parser.parse_args()
    asyncio.run(seed(args.products, args.orders))
