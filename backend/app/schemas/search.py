from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.schemas.catalog import ProductOut


class SearchSort(StrEnum):
    relevance = "relevance"
    newest = "newest"
    price_asc = "price_asc"
    price_desc = "price_desc"


class SearchParams(BaseModel):
    q: str | None = Field(None, max_length=200)
    brand: list[str] = Field(default_factory=list, max_length=20)
    category: list[str] = Field(default_factory=list, max_length=20)
    color: list[str] = Field(default_factory=list, max_length=20)
    size: list[str] = Field(default_factory=list, max_length=20)
    min_price: int | None = Field(None, ge=0, description="In paise")
    max_price: int | None = Field(None, ge=0, description="In paise")
    in_stock: bool = False
    sort: SearchSort = SearchSort.relevance
    page: int = Field(1, ge=1, le=400)
    per_page: int = Field(24, ge=1, le=50)

    @model_validator(mode="after")
    def check_price_range(self) -> "SearchParams":
        if self.min_price is not None and self.max_price is not None and self.max_price < self.min_price:
            raise ValueError("max_price must be greater than or equal to min_price")
        return self


class Facet(BaseModel):
    value: str
    count: int


class SearchOut(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    per_page: int
    facets: dict[str, list[Facet]] | None = Field(description="None when search fell back to the database")
    engine: str = Field(description='"opensearch", or "database" if the search engine was unavailable')
