import os
from typing import List

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from playwright.sync_api import Error, Page, sync_playwright

from django_components import types

from .django_test_setup import setup_test_config

setup_test_config(
    components={"autodiscover": False},
    extra_settings={
        "ROOT_URLCONF": "tests.test_dependency_manager",
    },
)

# NOTE: Playwright's Page.evaluate introduces async code. To ignore it,
# we set the following env var.
# See https://stackoverflow.com/a/67042751/9788634
# And https://docs.djangoproject.com/en/5.1/topics/async/#asgiref.sync.sync_to_async
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

urlpatterns: List = []


@override_settings(STATIC_URL="static/")
class DependencyManagerTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()

    def _create_page_with_dep_manager(self) -> Page:
        page = self.browser.new_page()
        # Load the JS library by opening a page with the script, and then running the script code
        # E.g. `http://localhost:54017/static/django_components/django_components.min.js`
        script_url = self.live_server_url + "/static/django_components/django_components.min.js"
        page.goto(script_url)
        page.evaluate(
            """() => {
            eval(document.body.textContent);
        }"""
        )

        # Ensure the body is clear
        page.evaluate(
            """() => {
            document.body.innerHTML = '';
            document.head.innerHTML = '';
        }"""
        )

        return page

    def test_script_loads(self):
        page = self._create_page_with_dep_manager()

        # Check the exposed API
        keys = sorted(page.evaluate("Object.keys(Components)"))
        self.assertEqual(keys, ["createComponentsManager", "manager", "unescapeJs"])

        keys = page.evaluate("Object.keys(Components.manager)")
        self.assertEqual(
            keys, ["callComponent", "registerComponent", "registerComponentData", "loadScript", "markScriptLoaded"]
        )

        page.close()


# Tests for `manager.loadScript()` / `manager.markAsLoaded()`
@override_settings(STATIC_URL="static/")
class LoadScriptTests(DependencyManagerTests):
    def test_load_js_scripts(self):
        page = self._create_page_with_dep_manager()

        # JS code that loads a few dependencies, capturing the HTML after each action
        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const headBeforeFirstLoad = document.head.innerHTML;

            // Adds a script the first time
            manager.loadScript('js', "<script src='/one/two'></script>");
            const bodyAfterFirstLoad = document.body.innerHTML;

            // Does not add it the second time
            manager.loadScript('js', "<script src='/one/two'></script>");
            const bodyAfterSecondLoad = document.body.innerHTML;

            // Adds different script
            manager.loadScript('js', "<script src='/four/three'></script>");
            const bodyAfterThirdLoad = document.body.innerHTML;

            const headAfterThirdLoad = document.head.innerHTML;

            return {
                bodyAfterFirstLoad,
                bodyAfterSecondLoad,
                bodyAfterThirdLoad,
                headBeforeFirstLoad,
                headAfterThirdLoad,
            };
        }"""

        data = page.evaluate(test_js)

        self.assertEqual(data["bodyAfterFirstLoad"], '<script src="/one/two"></script>')
        self.assertEqual(data["bodyAfterSecondLoad"], '<script src="/one/two"></script>')
        self.assertEqual(
            data["bodyAfterThirdLoad"], '<script src="/one/two"></script><script src="/four/three"></script>'
        )

        self.assertEqual(data["headBeforeFirstLoad"], data["headAfterThirdLoad"])
        self.assertEqual(data["headBeforeFirstLoad"], "")

        page.close()

    def test_load_css_scripts(self):
        page = self._create_page_with_dep_manager()

        # JS code that loads a few dependencies, capturing the HTML after each action
        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const bodyBeforeFirstLoad = document.body.innerHTML;

            // Adds a script the first time
            manager.loadScript('css', "<link href='/one/two'>");
            const headAfterFirstLoad = document.head.innerHTML;

            // Does not add it the second time
            manager.loadScript('css', "<link herf='/one/two'>");
            const headAfterSecondLoad = document.head.innerHTML;

            // Adds different script
            manager.loadScript('css', "<link href='/four/three'>");
            const headAfterThirdLoad = document.head.innerHTML;

            const bodyAfterThirdLoad = document.body.innerHTML;

            return {
                headAfterFirstLoad,
                headAfterSecondLoad,
                headAfterThirdLoad,
                bodyBeforeFirstLoad,
                bodyAfterThirdLoad,
            };
        }"""

        data = page.evaluate(test_js)

        self.assertEqual(data["headAfterFirstLoad"], '<link href="/one/two">')
        self.assertEqual(data["headAfterSecondLoad"], '<link href="/one/two">')
        self.assertEqual(data["headAfterThirdLoad"], '<link href="/one/two"><link href="/four/three">')

        self.assertEqual(data["bodyBeforeFirstLoad"], data["bodyAfterThirdLoad"])
        self.assertEqual(data["bodyBeforeFirstLoad"], "")

        page.close()

    def test_does_not_load_script_if_marked_as_loaded(self):
        page = self._create_page_with_dep_manager()

        # JS code that loads a few dependencies, capturing the HTML after each action
        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            // Adds a script the first time
            manager.markScriptLoaded('css', '/one/two');
            manager.markScriptLoaded('js', '/one/three');

            manager.loadScript('css', "<link href='/one/two'>");
            const headAfterFirstLoad = document.head.innerHTML;

            manager.loadScript('js', "<script src='/one/three'></script>");
            const bodyAfterSecondLoad = document.body.innerHTML;

            return {
                headAfterFirstLoad,
                bodyAfterSecondLoad,
            };
        }"""

        data = page.evaluate(test_js)

        self.assertEqual(data["headAfterFirstLoad"], "")
        self.assertEqual(data["bodyAfterSecondLoad"], "")

        page.close()


# Tests for `manager.registerComponent()` / `registerComponentData()` / `callComponent()`
@override_settings(STATIC_URL="static/")
class CallComponentTests(DependencyManagerTests):
    def test_calls_component_successfully(self):
        page = self._create_page_with_dep_manager()

        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const compName = 'my_comp';
            const compId = '12345';
            const inputHash = 'input-abc';

            // Pretend that this HTML belongs to our component
            document.body.insertAdjacentHTML('beforeend', '<div data-comp-id-12345> abc </div>');

            let capturedCtx = null;
            manager.registerComponent(compName, (ctx) => {
                capturedCtx = ctx;
                return 123;
            });

            manager.registerComponentData(compName, inputHash, () => {
                return { hello: 'world' };
            });

            const result = manager.callComponent(compName, compId, inputHash);

            // Serialize the HTML elements
            capturedCtx.$els = capturedCtx.$els.map((el) => el.outerHTML);

            return {
              result,
              capturedCtx,
            };
        }"""

        data = page.evaluate(test_js)

        self.assertEqual(data["result"], 123)
        self.assertEqual(
            data["capturedCtx"],
            {
                "$data": {
                    "hello": "world",
                },
                "$els": ['<div data-comp-id-12345=""> abc </div>'],
                "$id": "12345",
                "$name": "my_comp",
            },
        )

        page.close()

    def test_calls_component_successfully_async(self):
        page = self._create_page_with_dep_manager()

        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const compName = 'my_comp';
            const compId = '12345';
            const inputHash = 'input-abc';

            // Pretend that this HTML belongs to our component
            document.body.insertAdjacentHTML('beforeend', '<div data-comp-id-12345> abc </div>');

            manager.registerComponent(compName, (ctx) => {
                return Promise.resolve(123);
            });

            manager.registerComponentData(compName, inputHash, () => {
                return { hello: 'world' };
            });

            // Should be Promise
            const result = manager.callComponent(compName, compId, inputHash);
            const isPromise = `${result}` === '[object Promise]';

            // Wrap the whole response in Promise, so we can add extra fields
            return Promise.resolve(result).then((res) => ({
              result: res,
              isPromise,
            }));
        }"""

        data = page.evaluate(test_js)

        self.assertEqual(data["result"], 123)
        self.assertEqual(data["isPromise"], True)

        page.close()

    def test_error_in_component_call_do_not_propagate_sync(self):
        page = self._create_page_with_dep_manager()

        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const compName = 'my_comp';
            const compId = '12345';
            const inputHash = 'input-abc';

            // Pretend that this HTML belongs to our component
            document.body.insertAdjacentHTML('beforeend', '<div data-comp-id-12345> abc </div>');

            manager.registerComponent(compName, (ctx) => {
                throw Error('Oops!');
                return 123;
            });

            manager.registerComponentData(compName, inputHash, () => {
                return { hello: 'world' };
            });

            const result = manager.callComponent(compName, compId, inputHash);

            return result;
        }"""

        data = page.evaluate(test_js)

        self.assertEqual(data, None)

        page.close()

    def test_error_in_component_call_do_not_propagate_async(self):
        page = self._create_page_with_dep_manager()

        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const compName = 'my_comp';
            const compId = '12345';
            const inputHash = 'input-abc';

            // Pretend that this HTML belongs to our component
            document.body.insertAdjacentHTML('beforeend', '<div data-comp-id-12345> abc </div>');

            manager.registerComponent(compName, async (ctx) => {
                throw Error('Oops!');
                return 123;
            });

            manager.registerComponentData(compName, inputHash, () => {
                return { hello: 'world' };
            });

            const result = manager.callComponent(compName, compId, inputHash);
            return Promise.allSettled([result]);
        }"""

        data = page.evaluate(test_js)

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["status"], "rejected")
        self.assertIsInstance(data[0]["reason"], Error)
        self.assertEqual(data[0]["reason"].message, "Oops!")

        page.close()

    def test_raises_if_component_element_not_in_dom(self):
        page = self._create_page_with_dep_manager()

        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const compName = 'my_comp';
            const compId = '12345';
            const inputHash = 'input-abc';

            manager.registerComponent(compName, (ctx) => {
                return 123;
            });

            manager.registerComponentData(compName, inputHash, () => {
                return { hello: 'world' };
            });

            // Should raise Error
            manager.callComponent(compName, compId, inputHash);
        }"""

        with self.assertRaisesMessage(
            Error, "Error: [Components] 'my_comp': No elements with component ID '12345' found"
        ):
            page.evaluate(test_js)

        page.close()

    def test_raises_if_input_hash_not_registered(self):
        page = self._create_page_with_dep_manager()

        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const compName = 'my_comp';
            const compId = '12345';
            const inputHash = 'input-abc';

            document.body.insertAdjacentHTML('beforeend', '<div data-comp-id-12345> abc </div>');

            manager.registerComponent(compName, (ctx) => {
                return Promise.resolve(123);
            });

            // Should raise Error
            manager.callComponent(compName, compId, inputHash);
        }"""

        with self.assertRaisesMessage(Error, "Error: [Components] 'my_comp': Cannot find input for hash 'input-abc'"):
            page.evaluate(test_js)

        page.close()

    def test_raises_if_component_not_registered(self):
        page = self._create_page_with_dep_manager()

        test_js: types.js = """() => {
            const manager = Components.createComponentsManager();

            const compName = 'my_comp';
            const compId = '12345';
            const inputHash = 'input-abc';

            document.body.insertAdjacentHTML('beforeend', '<div data-comp-id-12345> abc </div>');

            manager.registerComponentData(compName, inputHash, () => {
                return { hello: 'world' };
            });

            // Should raise Error
            manager.callComponent(compName, compId, inputHash);
        }"""

        with self.assertRaisesMessage(Error, "Error: [Components] 'my_comp': No component registered for that name"):
            page.evaluate(test_js)

        page.close()
