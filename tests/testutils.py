from django.test import SimpleTestCase


class Django30CompatibleSimpleTestCase(SimpleTestCase):
    def assertHTMLEqual(self, left, right):
        left = left.replace(' type="text/javascript"', '')
        super(Django30CompatibleSimpleTestCase, self).assertHTMLEqual(left, right)
