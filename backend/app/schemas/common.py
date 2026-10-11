from pydantic import BaseModel


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    per_page: int


class Message(BaseModel):
    detail: str
