from typing import List

from .element import Element


class Children:
    def children(self) -> List[Element]:
        return []

    def add_element(self, ele: Element) -> Element:
        self.children().append(ele)
        ele.parent = self
        return ele
