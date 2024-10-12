import functools
from typing import Any, Callable, TypeVar, cast

TFunc = TypeVar("TFunc", bound=Callable)


def lazy_cache(
    make_cache: Callable[[], Callable[[Callable], Callable]],
) -> Callable[[TFunc], TFunc]:
    """
    Decorator that caches the given function similarly to `functools.lru_cache`.
    But the cache is instantiated only at first invocation.

    `cache` argument is a function that generates the cache function,
    e.g. `functools.lru_cache()`.
    """
    _cached_fn = None

    def decorator(fn: TFunc) -> TFunc:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Lazily initialize the cache
            nonlocal _cached_fn
            if not _cached_fn:
                # E.g. `lambda: functools.lru_cache(maxsize=app_settings.TEMPLATE_CACHE_SIZE)`
                cache = make_cache()
                _cached_fn = cache(fn)

            return _cached_fn(*args, **kwargs)

        # Allow to access the LRU cache methods
        # See https://stackoverflow.com/a/37654201/9788634
        wrapper.cache_info = lambda: _cached_fn.cache_info()  # type: ignore
        wrapper.cache_clear = lambda: _cached_fn.cache_clear()  # type: ignore

        # And allow to remove the cache instance (mostly for tests)
        def cache_remove() -> None:
            nonlocal _cached_fn
            _cached_fn = None

        wrapper.cache_remove = cache_remove  # type: ignore

        return cast(TFunc, wrapper)

    return decorator
