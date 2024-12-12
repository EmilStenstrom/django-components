"""
Here we check that all parts of managing JS and CSS dependencies work together
in an actual browser.
"""

from playwright.async_api import Page

from django_components import types
from tests.django_test_setup import setup_test_config
from tests.e2e.utils import TEST_SERVER_URL, with_playwright
from tests.testutils import BaseTestCase

setup_test_config({"autodiscover": False})


# NOTE: All views, components,  and associated JS and CSS are defined in
# `tests/e2e/testserver/testserver`
class E2eDependencyRenderingTests(BaseTestCase):
    @with_playwright
    async def test_single_component_dependencies(self):
        single_comp_url = TEST_SERVER_URL + "/single"

        page: Page = await self.browser.new_page()
        await page.goto(single_comp_url)

        test_js: types.js = """() => {
            const bodyHTML = document.body.innerHTML;

            const innerEl = document.querySelector(".inner");
            const innerFontSize = globalThis.getComputedStyle(innerEl).getPropertyValue('font-size');

            const myStyleEl = document.querySelector(".my-style");
            const myStyleBg = globalThis.getComputedStyle(myStyleEl).getPropertyValue('background');

            return {
                bodyHTML,
                componentJsMsg: globalThis.testSimpleComponent,
                scriptJsMsg: globalThis.testMsg,
                innerFontSize,
                myStyleBg,
            };
        }"""

        data = await page.evaluate(test_js)

        # Check that the actual HTML content was loaded
        self.assertIn('Variable: <strong class="inner">foo</strong>', data["bodyHTML"])
        self.assertInHTML('<div class="my-style"> 123 </div>', data["bodyHTML"], count=1)
        self.assertInHTML('<div class="my-style2"> xyz </div>', data["bodyHTML"], count=1)

        # Check components' inlined JS got loaded
        self.assertEqual(data["componentJsMsg"], "kapowww!")

        # Check JS from Media.js got loaded
        self.assertEqual(data["scriptJsMsg"], {"hello": "world"})

        # Check components' inlined CSS got loaded
        self.assertEqual(data["innerFontSize"], "4px")

        # Check CSS from Media.css got loaded
        self.assertIn("rgb(0, 0, 255)", data["myStyleBg"])  # AKA 'background: blue'

        await page.close()

    @with_playwright
    async def test_multiple_component_dependencies(self):
        single_comp_url = TEST_SERVER_URL + "/multi"

        page: Page = await self.browser.new_page()
        await page.goto(single_comp_url)

        test_js: types.js = """() => {
            const bodyHTML = document.body.innerHTML;

            // Get the stylings defined via CSS
            const innerEl = document.querySelector(".inner");
            const innerFontSize = globalThis.getComputedStyle(innerEl).getPropertyValue('font-size');

            const outerEl = document.querySelector(".outer");
            const outerFontSize = globalThis.getComputedStyle(outerEl).getPropertyValue('font-size');

            const otherEl = document.querySelector(".other");
            const otherDisplay = globalThis.getComputedStyle(otherEl).getPropertyValue('display');

            const myStyleEl = document.querySelector(".my-style");
            const myStyleBg = globalThis.getComputedStyle(myStyleEl).getPropertyValue('background');

            const myStyle2El = document.querySelector(".my-style2");
            const myStyle2Color = globalThis.getComputedStyle(myStyle2El).getPropertyValue('color');

            return {
                bodyHTML,
                component1JsMsg: globalThis.testSimpleComponent,
                component2JsMsg: globalThis.testSimpleComponentNested,
                component3JsMsg: globalThis.testOtherComponent,
                scriptJs1Msg: globalThis.testMsg,
                scriptJs2Msg: globalThis.testMsg2,
                innerFontSize,
                outerFontSize,
                myStyleBg,
                myStyle2Color,
                otherDisplay,
            };
        }"""

        data = await page.evaluate(test_js)

        # Check that the actual HTML content was loaded
        self.assertInHTML(
            """
            <div class="outer">
                Variable: <strong class="inner">variable</strong>
                XYZ: <strong class="other">variable_inner</strong>
            </div>
            <div class="my-style">123</div>
            <div class="my-style2">xyz</div>
            """,
            data["bodyHTML"],
            count=1,
        )

        # Check components' inlined JS got loaded
        self.assertEqual(data["component1JsMsg"], "kapowww!")
        self.assertEqual(data["component2JsMsg"], "bongo!")
        self.assertEqual(data["component3JsMsg"], "wowzee!")

        # Check JS from Media.js got loaded
        self.assertEqual(data["scriptJs1Msg"], {"hello": "world"})
        self.assertEqual(data["scriptJs2Msg"], {"hello2": "world2"})

        # Check components' inlined CSS got loaded
        self.assertEqual(data["innerFontSize"], "4px")
        self.assertEqual(data["outerFontSize"], "40px")
        self.assertEqual(data["otherDisplay"], "flex")

        # Check CSS from Media.css got loaded
        self.assertIn("rgb(0, 0, 255)", data["myStyleBg"])  # AKA 'background: blue'
        self.assertEqual("rgb(255, 0, 0)", data["myStyle2Color"])  # AKA 'color: red'

        await page.close()

    @with_playwright
    async def test_renders_css_nojs_env(self):
        single_comp_url = TEST_SERVER_URL + "/multi"

        page: Page = await self.browser.new_page(java_script_enabled=False)
        await page.goto(single_comp_url)

        test_js: types.js = """() => {
            const bodyHTML = document.body.innerHTML;

            // Get the stylings defined via CSS
            const innerEl = document.querySelector(".inner");
            const innerFontSize = globalThis.getComputedStyle(innerEl).getPropertyValue('font-size');

            const outerEl = document.querySelector(".outer");
            const outerFontSize = globalThis.getComputedStyle(outerEl).getPropertyValue('font-size');

            const otherEl = document.querySelector(".other");
            const otherDisplay = globalThis.getComputedStyle(otherEl).getPropertyValue('display');

            const myStyleEl = document.querySelector(".my-style");
            const myStyleBg = globalThis.getComputedStyle(myStyleEl).getPropertyValue('background');

            const myStyle2El = document.querySelector(".my-style2");
            const myStyle2Color = globalThis.getComputedStyle(myStyle2El).getPropertyValue('color');

            return {
                bodyHTML,
                component1JsMsg: globalThis.testSimpleComponent,
                component2JsMsg: globalThis.testSimpleComponentNested,
                component3JsMsg: globalThis.testOtherComponent,
                scriptJs1Msg: globalThis.testMsg,
                scriptJs2Msg: globalThis.testMsg2,
                innerFontSize,
                outerFontSize,
                myStyleBg,
                myStyle2Color,
                otherDisplay,
            };
        }"""

        data = await page.evaluate(test_js)

        # Check that the actual HTML content was loaded
        self.assertInHTML(
            """
            <div class="outer">
                Variable: <strong class="inner">variable</strong>
                XYZ: <strong class="other">variable_inner</strong>
            </div>
            <div class="my-style">123</div>
            <div class="my-style2">xyz</div>
            """,
            data["bodyHTML"],
            count=1,
        )

        # Check components' inlined JS did NOT get loaded
        self.assertEqual(data["component1JsMsg"], None)
        self.assertEqual(data["component2JsMsg"], None)
        self.assertEqual(data["component3JsMsg"], None)

        # Check JS from Media.js did NOT get loaded
        self.assertEqual(data["scriptJs1Msg"], None)
        self.assertEqual(data["scriptJs2Msg"], None)

        # Check components' inlined CSS got loaded
        self.assertEqual(data["innerFontSize"], "4px")
        self.assertEqual(data["outerFontSize"], "40px")
        self.assertEqual(data["otherDisplay"], "flex")

        # Check CSS from Media.css got loaded
        self.assertIn("rgb(0, 0, 255)", data["myStyleBg"])  # AKA 'background: blue'
        self.assertEqual("rgb(255, 0, 0)", data["myStyle2Color"])  # AKA 'color: red'

        await page.close()

    @with_playwright
    async def test_js_executed_in_order__js(self):
        single_comp_url = TEST_SERVER_URL + "/js-order/js"

        page: Page = await self.browser.new_page()
        await page.goto(single_comp_url)

        test_js: types.js = """() => {
            // NOTE: This variable should be defined by `check_script_order` component,
            // and it should contain all other variables defined by the previous components
            return checkVars;
        }"""

        data = await page.evaluate(test_js)

        # Check components' inlined JS got loaded
        self.assertEqual(data["testSimpleComponent"], "kapowww!")
        self.assertEqual(data["testSimpleComponentNested"], "bongo!")
        self.assertEqual(data["testOtherComponent"], "wowzee!")

        # Check JS from Media.js got loaded
        self.assertEqual(data["testMsg"], {"hello": "world"})
        self.assertEqual(data["testMsg2"], {"hello2": "world2"})

        await page.close()

    @with_playwright
    async def test_js_executed_in_order__media(self):
        single_comp_url = TEST_SERVER_URL + "/js-order/media"

        page: Page = await self.browser.new_page()
        await page.goto(single_comp_url)

        test_js: types.js = """() => {
            // NOTE: This variable should be defined by `check_script_order` component,
            // and it should contain all other variables defined by the previous components
            return checkVars;
        }"""

        data = await page.evaluate(test_js)

        # Check components' inlined JS got loaded
        # NOTE: The Media JS are loaded BEFORE the components' JS, so they should be empty
        self.assertEqual(data["testSimpleComponent"], None)
        self.assertEqual(data["testSimpleComponentNested"], None)
        self.assertEqual(data["testOtherComponent"], None)

        # Check JS from Media.js
        self.assertEqual(data["testMsg"], {"hello": "world"})
        self.assertEqual(data["testMsg2"], {"hello2": "world2"})

        await page.close()

    # In this case the component whose JS is accessing data from other components
    # is used in the template before the other components. So the JS should
    # not be able to access the data from the other components.
    @with_playwright
    async def test_js_executed_in_order__invalid(self):
        single_comp_url = TEST_SERVER_URL + "/js-order/invalid"

        page: Page = await self.browser.new_page()
        await page.goto(single_comp_url)

        test_js: types.js = """() => {
            // checkVars was defined BEFORE other components, so it should be empty!
            return checkVars;
        }"""

        data = await page.evaluate(test_js)

        # Check components' inlined JS got loaded
        self.assertEqual(data["testSimpleComponent"], None)
        self.assertEqual(data["testSimpleComponentNested"], None)
        self.assertEqual(data["testOtherComponent"], None)

        # Check JS from Media.js got loaded
        self.assertEqual(data["testMsg"], None)
        self.assertEqual(data["testMsg2"], None)

        await page.close()

    # Fragment where JS and CSS is defined on Component class
    @with_playwright
    async def test_fragment_comp(self):
        page: Page = await self.browser.new_page()
        await page.goto(f"{TEST_SERVER_URL}/fragment/base/js?frag=comp")

        test_before_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragHtml = fragEl ? fragEl.outerHTML : null;

            return { targetHtml, fragHtml };
        }"""

        data_before = await page.evaluate(test_before_js)

        self.assertEqual(data_before["targetHtml"], '<div id="target">OLD</div>')
        self.assertEqual(data_before["fragHtml"], None)

        # Clicking button should load and insert the fragment
        await page.locator("button").click()

        # Wait until both JS and CSS are loaded
        await page.locator(".frag").wait_for(state="visible")
        await page.wait_for_function(
            "() => document.head.innerHTML.includes('<link href=\"/components/cache/FragComp_')"
        )
        await page.wait_for_timeout(100)  # NOTE: For CI we need to wait a bit longer

        test_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragHtml = fragEl ? fragEl.outerHTML : null;

            // Get the stylings defined via CSS
            const fragBg = fragEl ? globalThis.getComputedStyle(fragEl).getPropertyValue('background') : null;

            return { targetHtml, fragHtml, fragBg };
        }"""

        data = await page.evaluate(test_js)

        self.assertEqual(data["targetHtml"], None)
        self.assertHTMLEqual('<div class="frag"> 123 <span id="frag-text">xxx</span></div>', data["fragHtml"])
        self.assertIn("rgb(0, 0, 255)", data["fragBg"])  # AKA 'background: blue'

        await page.close()

    # Fragment where JS and CSS is defined on Media class
    @with_playwright
    async def test_fragment_media(self):
        page: Page = await self.browser.new_page()
        await page.goto(f"{TEST_SERVER_URL}/fragment/base/js?frag=media")

        test_before_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragHtml = fragEl ? fragEl.outerHTML : null;

            return { targetHtml, fragHtml };
        }"""

        data_before = await page.evaluate(test_before_js)

        self.assertEqual(data_before["targetHtml"], '<div id="target">OLD</div>')
        self.assertEqual(data_before["fragHtml"], None)

        # Clicking button should load and insert the fragment
        await page.locator("button").click()

        # Wait until both JS and CSS are loaded
        await page.locator(".frag").wait_for(state="visible")
        await page.wait_for_function("() => document.head.innerHTML.includes('<link href=\"/static/fragment.css\"')")
        await page.wait_for_timeout(100)  # NOTE: For CI we need to wait a bit longer

        test_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragHtml = fragEl ? fragEl.outerHTML : null;

            // Get the stylings defined via CSS
            const fragBg = fragEl ? globalThis.getComputedStyle(fragEl).getPropertyValue('background') : null;

            return { targetHtml, fragHtml, fragBg };
        }"""

        data = await page.evaluate(test_js)

        self.assertEqual(data["targetHtml"], None)
        self.assertHTMLEqual('<div class="frag"> 123 <span id="frag-text">xxx</span></div>', data["fragHtml"])
        self.assertIn("rgb(0, 0, 255)", data["fragBg"])  # AKA 'background: blue'

        await page.close()

    # Fragment loaded by AlpineJS
    @with_playwright
    async def test_fragment_alpine(self):
        page: Page = await self.browser.new_page()
        await page.goto(f"{TEST_SERVER_URL}/fragment/base/alpine?frag=comp")

        test_before_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragHtml = fragEl ? fragEl.outerHTML : null;

            return { targetHtml, fragHtml };
        }"""

        data_before = await page.evaluate(test_before_js)

        self.assertEqual(data_before["targetHtml"], '<div id="target" x-html="htmlVar">OLD</div>')
        self.assertEqual(data_before["fragHtml"], None)

        # Clicking button should load and insert the fragment
        await page.locator("button").click()

        # Wait until both JS and CSS are loaded
        await page.locator(".frag").wait_for(state="visible")
        await page.wait_for_function(
            "() => document.head.innerHTML.includes('<link href=\"/components/cache/FragComp_')"
        )
        await page.wait_for_timeout(100)  # NOTE: For CI we need to wait a bit longer

        test_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragHtml = fragEl ? fragEl.outerHTML : null;

            // Get the stylings defined via CSS
            const fragBg = fragEl ? globalThis.getComputedStyle(fragEl).getPropertyValue('background') : null;

            return { targetHtml, fragHtml, fragBg };
        }"""

        data = await page.evaluate(test_js)

        # NOTE: Unlike the vanilla JS tests, for the Alpine test we don't remove the targetHtml,
        # but only change its contents.
        self.assertInHTML(
            '<div class="frag"> 123 <span id="frag-text">xxx</span></div>',
            data["targetHtml"],
        )
        self.assertHTMLEqual(data["fragHtml"], '<div class="frag"> 123 <span id="frag-text">xxx</span></div>')
        self.assertIn("rgb(0, 0, 255)", data["fragBg"])  # AKA 'background: blue'

        await page.close()

    # Fragment loaded by HTMX
    @with_playwright
    async def test_fragment_htmx(self):
        page: Page = await self.browser.new_page()
        await page.goto(f"{TEST_SERVER_URL}/fragment/base/htmx?frag=comp")

        test_before_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragHtml = fragEl ? fragEl.outerHTML : null;

            return { targetHtml, fragHtml };
        }"""

        data_before = await page.evaluate(test_before_js)

        self.assertEqual(data_before["targetHtml"], '<div id="target">OLD</div>')
        self.assertEqual(data_before["fragHtml"], None)

        # Clicking button should load and insert the fragment
        await page.locator("button").click()

        # Wait until both JS and CSS are loaded
        await page.locator(".frag").wait_for(state="visible")
        await page.wait_for_function(
            "() => document.head.innerHTML.includes('<link href=\"/components/cache/FragComp_')"
        )
        await page.wait_for_timeout(100)  # NOTE: For CI we need to wait a bit longer

        test_js: types.js = """() => {
            const targetEl = document.querySelector("#target");
            const targetHtml = targetEl ? targetEl.outerHTML : null;
            const fragEl = document.querySelector(".frag");
            const fragInnerHtml = fragEl ? fragEl.innerHTML : null;

            // Get the stylings defined via CSS
            const fragBg = fragEl ? globalThis.getComputedStyle(fragEl).getPropertyValue('background') : null;

            return { targetHtml, fragInnerHtml, fragBg };
        }"""

        data = await page.evaluate(test_js)

        self.assertEqual(data["targetHtml"], None)
        # NOTE: We test only the inner HTML, because the element itself may or may not have
        # extra CSS classes added by HTMX, which results in flaky tests.
        self.assertHTMLEqual(
            data["fragInnerHtml"],
            '123 <span id="frag-text">xxx</span>',
        )
        self.assertIn("rgb(0, 0, 255)", data["fragBg"])  # AKA 'background: blue'

        await page.close()

    @with_playwright
    async def test_alpine__head(self):
        single_comp_url = TEST_SERVER_URL + "/alpine/head"

        page: Page = await self.browser.new_page()
        await page.goto(single_comp_url)

        component_text = await page.locator('[x-data="alpine_test"]').text_content()
        self.assertHTMLEqual(component_text.strip(), "ALPINE_TEST: 123")

        await page.close()

    @with_playwright
    async def test_alpine__body(self):
        single_comp_url = TEST_SERVER_URL + "/alpine/body"

        page: Page = await self.browser.new_page()
        await page.goto(single_comp_url)

        component_text = await page.locator('[x-data="alpine_test"]').text_content()
        self.assertHTMLEqual(component_text.strip(), "ALPINE_TEST: 123")

        await page.close()

    @with_playwright
    async def test_alpine__body2(self):
        single_comp_url = TEST_SERVER_URL + "/alpine/body2"

        page: Page = await self.browser.new_page()
        await page.goto(single_comp_url)

        component_text = await page.locator('[x-data="alpine_test"]').text_content()
        self.assertHTMLEqual(component_text.strip(), "ALPINE_TEST: 123")

        await page.close()

    @with_playwright
    async def test_alpine__invalid(self):
        single_comp_url = TEST_SERVER_URL + "/alpine/invalid"

        page: Page = await self.browser.new_page()
        await page.goto(single_comp_url)

        component_text = await page.locator('[x-data="alpine_test"]').text_content()
        self.assertHTMLEqual(component_text.strip(), "ALPINE_TEST:")

        await page.close()
