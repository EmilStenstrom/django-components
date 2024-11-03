import glob
import re
from pathlib import Path
from typing import Any, Callable, List, Optional, Sequence, Type, TypeVar, Union

from django.template.defaultfilters import escape
from django.utils.autoreload import autoreload_started

from django_components.util.nanoid import generate

T = TypeVar("T")


# Based on nanoid implementation from
# https://github.com/puyuan/py-nanoid/tree/99e5b478c450f42d713b6111175886dccf16f156/nanoid
def gen_id() -> str:
    """Generate a unique ID that can be associated with a Node"""
    # Alphabet is only alphanumeric. Compared to the default alphabet used by nanoid,
    # we've omitted `-` and `_`.
    # With this alphabet, at 6 chars, the chance of collision is 1 in 3.3M.
    # See https://zelark.github.io/nano-id-cc/
    return generate(
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        size=6,
    )


def find_last_index(lst: List, predicate: Callable[[Any], bool]) -> Any:
    for r_idx, elem in enumerate(reversed(lst)):
        if predicate(elem):
            return len(lst) - 1 - r_idx
    return -1


def is_str_wrapped_in_quotes(s: str) -> bool:
    return s.startswith(('"', "'")) and s[0] == s[-1] and len(s) >= 2


# See https://github.com/EmilStenstrom/django-components/issues/586#issue-2472678136
def watch_files_for_autoreload(watch_list: Sequence[Union[str, Path]]) -> None:
    def autoreload_hook(sender: Any, *args: Any, **kwargs: Any) -> None:
        watch = sender.extra_files.add
        for file in watch_list:
            watch(Path(file))

    autoreload_started.connect(autoreload_hook)


def any_regex_match(string: str, patterns: List[re.Pattern]) -> bool:
    return any(p.search(string) is not None for p in patterns)


def no_regex_match(string: str, patterns: List[re.Pattern]) -> bool:
    return all(p.search(string) is None for p in patterns)


def search_dirs(dirs: List[Path], search_glob: str) -> List[Path]:
    """
    Search the directories for the given glob pattern. Glob search results are returned
    as a flattened list.
    """
    matched_files: List[Path] = []
    for directory in dirs:
        for path in glob.iglob(str(Path(directory) / search_glob), recursive=True):
            matched_files.append(Path(path))

    return matched_files


# See https://stackoverflow.com/a/2020083/9788634
def get_import_path(cls_or_fn: Type[Any]) -> str:
    """
    Get the full import path for a class or a function, e.g. `"path.to.MyClass"`
    """
    module = cls_or_fn.__module__
    if module == "builtins":
        return cls_or_fn.__qualname__  # avoid outputs like 'builtins.str'
    return module + "." + cls_or_fn.__qualname__


# See https://stackoverflow.com/a/58800331/9788634
# str.replace(/\\|`|\$/g, '\\$&');
JS_STRING_LITERAL_SPECIAL_CHARS_REGEX = re.compile(r"\\|`|\$")


# See https://stackoverflow.com/a/34064434/9788634
def escape_js_string_literal(js: str) -> str:
    escaped_js = escape(js)

    def on_replace_match(match: "re.Match[str]") -> str:
        return f"\\{match[0]}"

    escaped_js = JS_STRING_LITERAL_SPECIAL_CHARS_REGEX.sub(on_replace_match, escaped_js)
    return escaped_js


def default(val: Optional[T], default: T) -> T:
    return val if val is not None else default
