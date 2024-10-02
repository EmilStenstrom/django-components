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
