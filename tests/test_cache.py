from django.test import TestCase

from django_components.util.cache import LRUCache

from .django_test_setup import setup_test_config

setup_test_config({"autodiscover": False})


class CacheTests(TestCase):
    def test_cache(self):
        cache = LRUCache[int](maxsize=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("b"), 2)
        self.assertEqual(cache.get("c"), 3)

        cache.set("d", 4)

        self.assertEqual(cache.get("a"), None)
        self.assertEqual(cache.get("b"), 2)
        self.assertEqual(cache.get("c"), 3)
        self.assertEqual(cache.get("d"), 4)

        cache.set("e", 5)
        cache.set("f", 6)

        self.assertEqual(cache.get("b"), None)
        self.assertEqual(cache.get("c"), None)
        self.assertEqual(cache.get("d"), 4)
        self.assertEqual(cache.get("e"), 5)
        self.assertEqual(cache.get("f"), 6)

        cache.clear()

        self.assertEqual(cache.get("d"), None)
        self.assertEqual(cache.get("e"), None)
        self.assertEqual(cache.get("f"), None)
