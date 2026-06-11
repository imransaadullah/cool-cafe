"""Base response model that maps Prisma's camelCase attributes to snake_case fields."""

import re
from pydantic import BaseModel, model_validator

_camel_re = re.compile(r"(?<!^)(?=[A-Z])")


def camel_to_snake(name: str) -> str:
    return _camel_re.sub("_", name).lower()


class ORMModel(BaseModel):
    """Accepts Prisma model instances (camelCase attrs) and dicts with either casing."""

    @model_validator(mode="before")
    @classmethod
    def _normalize_keys(cls, data):
        if isinstance(data, BaseModel):
            data = {k: getattr(data, k) for k in type(data).model_fields}
        elif not isinstance(data, dict) and hasattr(data, "__dict__"):
            data = vars(data)
        if isinstance(data, dict):
            return {camel_to_snake(k): v for k, v in data.items()}
        return data

    class Config:
        from_attributes = True
