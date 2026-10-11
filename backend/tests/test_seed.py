from app.schemas.auth import LoginIn
from app.seed import DEMO_PASSWORD, DEMO_USERS


def test_demo_logins_pass_login_validation() -> None:
    """Reserved domains like .test fail email validation, which would lock out the demo accounts."""
    for email, _, _ in DEMO_USERS:
        LoginIn(email=email, password=DEMO_PASSWORD)
