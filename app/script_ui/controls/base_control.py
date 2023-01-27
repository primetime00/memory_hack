from typing import List

from .element import Element


class ControlException(Exception):
    pass

class BaseControl(Element):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def children(self) -> List[Element]:
        return []

    def add_element(self, ele: Element) -> Element:
        raise ControlException('Base Control has not children')



