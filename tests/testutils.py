from django.test import SimpleTestCase


class Django111CompatibleSimpleTestCase(SimpleTestCase):
    def assertHTMLEqual(self, left, right):
        left = left.replace(' type="text/javascript"', '')
        super(Django111CompatibleSimpleTestCase, self).assertHTMLEqual(left, right)
