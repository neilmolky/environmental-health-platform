from collections.abc import Iterator

from pydantic import BaseModel, Field, RootModel


class One[T: BaseModel](RootModel[tuple[T]]):
    @property
    def item(self) -> T:
        """
        Access the first (and expected only) element of the underlying root tuple.
        
        Returns:
            The element of type T stored at index 0 of the root tuple.
        """
        return self.root[0]


class Some[T: BaseModel](RootModel[list[T]]):
    root: list[T] = Field(min_length=1)

    @property
    def first(self) -> T:
        """
        Get the first element of the wrapped non-empty list.
        
        Returns:
            T: The first item in the underlying list.
        """
        return self.root[0]

    # Make the wrapper act exactly like a standard Python list
    def __iter__(self) -> Iterator[T]:  # type: ignore
        """
        Return an iterator over the wrapped items.
        
        Returns:
            Iterator[T]: An iterator that yields the underlying items in order.
        """
        return iter(self.root)

    def __len__(self) -> int:
        """
        Return the number of elements in the wrapped list.
        
        Returns:
            int: The number of items in the underlying `root` list.
        """
        return len(self.root)

    def __getitem__(self, index: int) -> T:
        """
        Retrieve the element at the given index from the wrapped list.
        
        Parameters:
            index (int): Position of the element to retrieve; negative indices count from the end.
        
        Returns:
            T: The element at the specified index.
        
        Raises:
            IndexError: If the index is out of range.
        """
        return self.root[index]
