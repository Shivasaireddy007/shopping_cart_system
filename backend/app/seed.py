"""Seed a demo catalog and logins.

    uv run python -m app.seed --products 1000

Safe to run repeatedly: it only adds products when the catalog is empty.
"""

import argparse
import asyncio
import random

from faker import Faker
from sqlalchemy import func, select

from app.core.security import hash_password
from app.core.text import slugify, unique_slug
from app.db import SessionLocal
from app.models import Category, Product, User

CATEGORIES = [
    "Running Shoes", "Sneakers", "Formal Shoes", "Sandals", "Boots", "T-Shirts", "Shirts", "Jeans",
    "Trousers", "Shorts", "Jackets", "Hoodies", "Track Pants", "Kurtas", "Watches", "Backpacks",
]  # fmt: skip
BRANDS = ["Nike", "Adidas", "Puma", "Reebok", "Bata", "Woodland", "Campus", "Sparx"]
COLORS = ["black", "white", "red", "blue", "green", "grey"]
SIZES = ["S", "M", "L", "XL"]

DEMO_USERS = [
    ("demo@shoppingcart.test", "Demo Customer", False),
    ("admin@shoppingcart.test", "Demo Admin", True),
]
DEMO_PASSWORD = "demo-password"


async def seed(product_count: int) -> None:
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
                name = fake.catch_phrase().title()
                price = random.randint(199, 9999) * 100
                session.add(
                    Product(
                        category_id=random.choice(categories).id,
                        sku="SKU-" + fake.unique.bothify("??########").upper(),
                        name=name,
                        slug=unique_slug(name),
                        description=fake.paragraph(),
                        brand=random.choice(BRANDS),
                        price=price,
                        mrp=round(price * random.choice([1, 1.1, 1.25, 1.5])),
                        stock=random.choice([0, *range(1, 200)]),
                        weight_grams=random.randint(100, 2000),
                        attributes={"color": random.choice(COLORS), "size": random.choice(SIZES)},
                    )
                )
            print(f"Seeded {product_count} products.")

        await session.commit()
    print(f"Logins: {', '.join(email for email, _, _ in DEMO_USERS)} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--products", type=int, default=1000)
    asyncio.run(seed(parser.parse_args().products))
