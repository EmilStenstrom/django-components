from django.test import TestCase, override_settings
from django.core.cache.backends.locmem import LocMemCache

from django_components.util.cache import LRUCache
from django_components import Component, register

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

    def test_cache_maxsize_zero(self):
        cache = LRUCache[int](maxsize=0)

        cache.set("a", 1)
        self.assertEqual(cache.get("a"), None)

        cache.set("b", 2)
        cache.set("c", 3)
        self.assertEqual(cache.get("b"), None)
        self.assertEqual(cache.get("c"), None)

        # Same with negative numbers
        cache = LRUCache[int](maxsize=-1)
        cache.set("a", 1)
        self.assertEqual(cache.get("a"), None)

        cache.set("b", 2)
        cache.set("c", 3)
        self.assertEqual(cache.get("b"), None)
        self.assertEqual(cache.get("c"), None)


class ComponentMediaCacheTests(TestCase):
    def setUp(self):
        # Create a custom locmem cache for testing
        self.test_cache = LocMemCache(
            "test-cache",
            {
                "TIMEOUT": None,  # No timeout
                "MAX_ENTRIES": None,  # No max size
                "CULL_FREQUENCY": 3,
            },
        )

    @override_settings(COMPONENTS={"cache": "test-cache"})
    def test_component_media_caching(self):
        @register("test_simple")
        class TestSimpleComponent(Component):
            template = """
                <div>Template only component</div>
            """

            def get_js_data(self):
                return {}

            def get_css_data(self):
                return {}

        @register("test_media_no_vars")
        class TestMediaNoVarsComponent(Component):
            template = """
                <div>Template and JS component</div>
                {% component "test_simple" / %}
            """
            js = "console.log('Hello from JS');"
            css = ".novars-component { color: blue; }"

            def get_js_data(self):
                return {}

            def get_css_data(self):
                return {}

        class TestMediaAndVarsComponent(Component):
            template = """
                <div>Full component</div>
                {% component "test_media_no_vars" / %}
            """
            js = "console.log('Hello from full component');"
            css = ".full-component { color: blue; }"

            def get_js_data(self):
                return {"message": "Hello"}

            def get_css_data(self):
                return {"color": "blue"}

        # Register our test cache
        from django.core.cache import caches

        caches["test-cache"] = self.test_cache

        # Render the components to trigger caching
        TestMediaAndVarsComponent.render()

        # Check that JS/CSS is cached for components that have them
        self.assertTrue(self.test_cache.has_key(f"__components:{TestMediaAndVarsComponent._class_hash}:js"))
        self.assertTrue(self.test_cache.has_key(f"__components:{TestMediaAndVarsComponent._class_hash}:css"))
        self.assertTrue(self.test_cache.has_key(f"__components:{TestMediaNoVarsComponent._class_hash}:js"))
        self.assertTrue(self.test_cache.has_key(f"__components:{TestMediaNoVarsComponent._class_hash}:css"))
        self.assertFalse(self.test_cache.has_key(f"__components:{TestSimpleComponent._class_hash}:js"))
        self.assertFalse(self.test_cache.has_key(f"__components:{TestSimpleComponent._class_hash}:css"))

        # Check that we cache `Component.js` / `Component.css`
        self.assertEqual(
            self.test_cache.get(f"__components:{TestMediaNoVarsComponent._class_hash}:js").strip(),
            "console.log('Hello from JS');",
        )
        self.assertEqual(
            self.test_cache.get(f"__components:{TestMediaNoVarsComponent._class_hash}:css").strip(),
            ".novars-component { color: blue; }",
        )

        # Check that we cache JS / CSS scripts generated from `get_js_data` / `get_css_data`
        # NOTE: The hashes is generated from the data.
        js_vars_hash = "216ecc"
        css_vars_hash = "d039a3"

        # TODO - Update once JS and CSS vars are enabled
        self.assertEqual(
            self.test_cache.get(f"__components:{TestMediaAndVarsComponent._class_hash}:js:{js_vars_hash}").strip(),
            "",
        )
        self.assertEqual(
            self.test_cache.get(f"__components:{TestMediaAndVarsComponent._class_hash}:css:{css_vars_hash}").strip(),
            "",
        )
