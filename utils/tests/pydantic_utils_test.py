import pytest
from pydantic import BaseModel, ValidationError
from utils.models.generic import One, Some


class Example(BaseModel):
    a: list[int]


def test_one() -> None:
    assert isinstance(One[Example].model_validate([{"a": []}]).item.a, list)
    assert isinstance(One[Example].model_validate([{"a": [1]}]).item, Example)
    with pytest.raises(ValidationError):
        One[Example].model_validate([])
    with pytest.raises(ValidationError):
        One[Example].model_validate([{"a": [1]}, {"a": [1]}])


def test_some() -> None:
    assert isinstance(Some[Example].model_validate([{"a": []}]).root, list)
    assert len(Some[Example].model_validate([{"a": [1]}, {"a": [1]}])) == 2
    with pytest.raises(ValidationError):
        Some[Example].model_validate([])
