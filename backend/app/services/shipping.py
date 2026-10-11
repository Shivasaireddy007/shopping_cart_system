from app.core.config import get_settings


def shipping_fee(subtotal: int) -> int:
    """Shipping fee in paise: free above the threshold, flat fee otherwise."""
    settings = get_settings()
    if subtotal == 0 or subtotal >= settings.shipping_free_above:
        return 0
    return settings.shipping_flat_fee
