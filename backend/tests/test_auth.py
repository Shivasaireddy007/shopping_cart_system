from httpx import AsyncClient

from tests.conftest import Factory, auth_header


async def test_register_returns_a_token_pair(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"name": "Asha", "email": "Asha@Example.com", "password": "secret-password"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.json()["email"] == "asha@example.com"


async def test_register_rejects_duplicate_email(client: AsyncClient, factory: Factory) -> None:
    await factory.user(email="taken@example.com")

    response = await client.post(
        "/api/v1/auth/register",
        json={"name": "X", "email": "taken@example.com", "password": "secret-password"},
    )

    assert response.status_code == 409


async def test_register_cannot_make_an_admin(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "Sneaky",
            "email": "sneaky@example.com",
            "password": "secret-password",
            "is_admin": True,
        },
    )
    token = response.json()["access_token"]

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["is_admin"] is False


async def test_login(client: AsyncClient, factory: Factory) -> None:
    user = await factory.user()

    ok = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password123"})
    bad = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "wrong"})

    assert ok.status_code == 200
    assert bad.status_code == 401


async def test_me_requires_a_valid_access_token(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nope"})).status_code == 401


async def test_refresh_token_cannot_be_used_as_access_token(client: AsyncClient, factory: Factory) -> None:
    user = await factory.user()
    tokens = (
        await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password123"})
    ).json()

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
    )

    assert response.status_code == 401


async def test_refresh_issues_a_new_pair(client: AsyncClient, factory: Factory) -> None:
    user = await factory.user()
    tokens = (
        await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password123"})
    ).json()

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    new_access = response.json()["access_token"]
    assert new_access != tokens["access_token"]
    assert (
        await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    ).status_code == 200


async def test_access_token_cannot_be_used_to_refresh(client: AsyncClient, factory: Factory) -> None:
    user = await factory.user()

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": auth_header(user)["Authorization"].removeprefix("Bearer ")},
    )

    assert response.status_code == 401
