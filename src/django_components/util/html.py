from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Sequence

from bs4 import BeautifulSoup, CData, Comment, Doctype, NavigableString, Tag


class HTMLNode(ABC):
    """
    Interface for an HTML manipulation library. This allows us to potentially swap
    between different libraries.
    """

    @classmethod
    @abstractmethod
    def from_fragment(cls, html: str) -> Sequence["HTMLNode"]: ...  # noqa: E704

    @abstractmethod
    def to_html(self) -> str: ...  # noqa: E704

    @abstractmethod
    def name(self) -> str:
        """Get tag name"""
        ...

    @abstractmethod
    def find_tag(self, tag: str) -> Optional["HTMLNode"]: ...  # noqa: E704

    @abstractmethod
    def children(self) -> Sequence["HTMLNode"]: ...  # noqa: E704

    @abstractmethod
    def append_children(self, children: Sequence[Any]) -> None: ...  # noqa: E704

    @abstractmethod
    def get_attr(self, attr: str, default: Any = None) -> Any: ...  # noqa: E704

    @abstractmethod
    def set_attr(self, attr: str, value: Any) -> None: ...  # noqa: E704

    @abstractmethod
    def get_attrs(self) -> Dict[str, Any]: ...  # noqa: E704

    @abstractmethod
    def is_element(self) -> bool: ...  # noqa: E704

    """Returns `False` if the node is a text, comment, or doctype node. `True` otherwise."""

    @classmethod
    def to_html_multiroot(cls, elems: Sequence["HTMLNode"]) -> str:
        return "".join([elem.to_html() for elem in elems])

    def walk(self, on_node: Callable[["HTMLNode", Callable], None]) -> None:
        stack: List["HTMLNode"] = [self]
        while stack:
            current = stack.pop()
            will_stop = False

            def stop() -> None:
                nonlocal will_stop
                will_stop = True

            on_node(current, stop)

            # If the stop function WAS called, we don't walk the children of the current node
            if not will_stop and current.is_element():
                stack.extend(current.children())


class SoupNode(HTMLNode):
    """BeautifulSoup implementation of HTMLNode."""

    def __init__(self, node: Tag):
        self.node = node

    @classmethod
    def from_fragment(cls, html: str) -> List["SoupNode"]:
        soup = BeautifulSoup(html, "html.parser")
        # Get top-level elements in the fragment
        return [cls(elem) for elem in soup.contents]

    def to_html(self) -> str:
        if isinstance(self.node, CData):
            return f"<![CDATA[{self.node}]]>"
        elif isinstance(self.node, Comment):
            return f"<!-- {self.node} -->"
        elif isinstance(self.node, Doctype):
            return f"<!DOCTYPE {self.node}>"
        elif isinstance(self.node, NavigableString):
            return str(self.node)
        else:
            # See https://github.com/EmilStenstrom/django-components/pull/861#discussion_r1898516210
            return self.node.encode(formatter="html5").decode()

    def name(self) -> str:
        return self.node.name

    def find_tag(self, tag: str) -> Optional["SoupNode"]:
        if isinstance(self.node, Tag) and self.node.name == tag:
            return self
        else:
            match = self.node.select_one(tag)
            if match:
                return SoupNode(match)
        return None

    def children(self) -> List["SoupNode"]:
        return [SoupNode(child) for child in self.node.children]

    def append_children(self, children: Sequence["SoupNode"]) -> None:
        if isinstance(self.node, Tag):
            for child in children:
                self.node.append(child.node)

    def get_attr(self, attr: str, default: Any = None) -> Any:
        if isinstance(self.node, Tag):
            res = self.node.get(attr, default)
            if isinstance(res, list):
                return " ".join(res)
            return res
        return default

    def set_attr(self, attr: str, value: Any) -> None:
        if not isinstance(self.node, Tag):
            return

        if value is True:
            # Set boolean attributes without a value
            self.node[attr] = None
        elif value is False:
            # Remove the attribute
            self.node.attrs.pop(attr, None)
        else:
            self.node[attr] = value

    def get_attrs(self) -> Dict[str, Any]:
        if isinstance(self.node, Tag):
            return self.node.attrs
        return {}

    def is_element(self) -> bool:
        return isinstance(self.node, Tag)

    def walk(self, on_node: Callable[["SoupNode", Callable], None]) -> None:
        return super().walk(on_node)  # type:ignore[arg-type]
