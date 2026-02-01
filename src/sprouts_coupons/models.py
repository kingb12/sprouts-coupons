from dataclasses import dataclass


@dataclass
class SessionInfo:
    """Session information extracted from browser login."""

    cookies: dict[str, str]
    shop_id: str
    user_name: str
    store_name: str


@dataclass
class Offer:
    """A coupon offer from Sprouts."""

    id: str
    offer_id: str
    coupon_id: str
    offer_request_key: str
    name: str
    description: str
    expires_on: str
    is_clipped: bool
    image_url: str | None = None

    def __str__(self) -> str:
        status = "CLIPPED" if self.is_clipped else "AVAILABLE"
        return f"[{status}] {self.name} - {self.description} (expires: {self.expires_on})"
