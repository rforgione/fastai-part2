# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/03_lesson4.ipynb (unless otherwise specified).

__all__ = ['A', 'B', 'Transform', 'compose', 'ItemList']

# Cell
from solutions.lesson1 import *
from solutions.lesson2 import *
from solutions.lesson3 import *
from typing import List, Sequence, TypeVar, Generic, Callable
from types import GeneratorType

# Cell
A = TypeVar('A')
B = TypeVar('B')

# Cell
class Transform(Generic[A,B]):
    _order = 0
    def __call__(self, x: A) -> B:
        raise NotImplementedError

# Cell
def compose(x: A, fs: Sequence[Callable[[A], A]]) -> A:
    sortd = sorted(fs, key=lambda x: getattr(x, '_order', 0))
    for f in sortd: x = f(x)
    return x

# Cell
class ItemList(ListContainer, Generic[A]):
    def __init__(self, items: List[A]):
        self.items = items

    def get(self, idx: int) -> A:
        return self.items[idx]

    def _get(self, idx, tfms: Sequence[Transform[A,A]]) -> A:
        if isinstance(tfms, (GeneratorType, set)): tfms = list(tfms)
        x = self.get(idx)
        return compose(x, tfms)