from .element import Element

class Children:
    def children(self) -> list[Element]:
        return []

    def add_element(self, ele: Element) -> Element:
        self.children().append(ele)
        ele.parent = self
        return ele
