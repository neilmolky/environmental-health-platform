from collections.abc import Iterator

from pydantic import BaseModel, Field, RootModel


class One[T: BaseModel](RootModel[tuple[T]]):
    @property
    def item(self) -> T:
        return self.root[0]


class Some[T: BaseModel](RootModel[list[T]]):
    root: list[T] = Field(min_length=1)

    @property
    def first(self) -> T:
        return self.root[0]

    # Make the wrapper act exactly like a standard Python list
    def __iter__(self) -> Iterator[T]:  # type: ignore
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)

    def __getitem__(self, index: int) -> T:
        return self.root[index]
