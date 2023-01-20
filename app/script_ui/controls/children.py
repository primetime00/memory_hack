from .element import Element
from typing import List

class Children:
    def children(self) -> List[Element]:
        return []

    def add_element(self, ele: Element) -> Element:
        self.children().append(ele)
        ele.parent = self
        return ele
