from abc import ABC, abstractmethod
from typing import Any, List, Optional, Sequence

from bs4 import BeautifulSoup, Tag


class HTMLNode(ABC):
    """
    Interface for an HTML manipulation library. This allows us to potentially swap
    between different libraries.
    """
    @classmethod
    @abstractmethod
    def from_fragment(cls, html: str) -> Sequence["HTMLNode"]: ...

    @abstractmethod
    def to_html(self) -> str: ...

    @abstractmethod
    def name(self) -> str: ...
    """Get tag name"""

    @abstractmethod
    def find_tag(self, tag: str) -> Optional["HTMLNode"]: ...

    @abstractmethod
    def append_children(self, children: Sequence[Any]) -> None: ...

    @abstractmethod
    def get_attr(self, attr: str, default: Any = None) -> Any: ...

    @abstractmethod
    def set_attr(self, attr: str, value: Any) -> None: ...

    @abstractmethod
    def is_element(self) -> bool: ...
    """Returns `False` if the node is a text, comment, or doctype node. `True` otherwise."""

    @classmethod
    def to_html_multiroot(cls, elems: Sequence["HTMLNode"]) -> str:
        return "".join([elem.to_html() for elem in elems])


class SoupNode(HTMLNode):
    """BeautifulSoup implementation of HTMLNode."""
    def __init__(self, node: Tag):
        self.node = node

    @classmethod
    def from_fragment(cls, html: str) -> List["SoupNode"]:
        soup = BeautifulSoup(html, 'html.parser')
        # Get top-level elements in the fragment
        return [cls(elem) for elem in soup.contents]

    def to_html(self) -> str:
        return str(self.node)
    
    def name(self) -> str:
        return self.node.name

    def find_tag(self, tag: str) -> Optional["SoupNode"]:
        if isinstance(self.node, Tag) and self.node.name == tag:
            return self
        else:
            match = self.node.find(tag)
            if match:
                return SoupNode(match)
        return None

    def append_children(self, children: Sequence["SoupNode"]) -> None:
        if isinstance(self.node, Tag):
            for child in children:
                self.node.append(child.node)

    def get_attr(self, attr: str, default: Any = None) -> Any:
        if isinstance(self.node, Tag):
            return self.node.get(attr, default)
        return default

    def set_attr(self, attr: str, value: Any) -> None:
        if isinstance(self.node, Tag):
            if value is True:
                # Set boolean attributes without a value
                self.node[attr] = None
            elif value is False:
                # Remove the attribute
                self.node.attrs.pop(attr, None)
            else:
                self.node[attr] = value

    def is_element(self) -> bool:
        return isinstance(self.node, Tag)
