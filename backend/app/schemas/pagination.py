from math import ceil
from typing import Generic, List, Sequence, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    page: int
    page_size: int
    total: int
    total_pages: int


def paginate_query(query, page: int, page_size: int) -> tuple[Sequence, int, int]:
    page = max(1, page)
    page_size = min(max(1, page_size), 200)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = ceil(total / page_size) if page_size else 0
    return items, total, total_pages


def pagination_params(
    page: int = Field(default=1, ge=1),
    page_size: int = Field(default=25, ge=1, le=200),
):
    return page, page_size
