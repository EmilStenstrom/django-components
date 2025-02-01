from django_components.util.component_highlight import apply_component_highlight, COLORS

from .django_test_setup import setup_test_config
from .testutils import BaseTestCase

setup_test_config({"autodiscover": False})


class ComponentHighlightTests(BaseTestCase):
    def test_component_highlight(self):
        # Test component highlighting
        test_html = "<div>Test content</div>"
        component_name = "TestComponent"
        result = apply_component_highlight("component", test_html, component_name)

        # Check that the output contains the component name
        self.assertIn(component_name, result)
        # Check that the output contains the original HTML
        self.assertIn(test_html, result)
        # Check that the component colors are used
        self.assertIn(COLORS["component"].text_color, result)
        self.assertIn(COLORS["component"].border_color, result)

    def test_slot_highlight(self):
        # Test slot highlighting
        test_html = "<span>Slot content</span>"
        slot_name = "content-slot"
        result = apply_component_highlight("slot", test_html, slot_name)

        # Check that the output contains the slot name
        self.assertIn(slot_name, result)
        # Check that the output contains the original HTML
        self.assertIn(test_html, result)
        # Check that the slot colors are used
        self.assertIn(COLORS["slot"].text_color, result)
        self.assertIn(COLORS["slot"].border_color, result)

    def test_highlight_styling(self):
        """Test that the output contains expected styling elements"""
        result = apply_component_highlight("component", "<p>Test</p>", "Test")

        # Check for expected styling elements
        self.assertIn("border-radius: 12px", result)
        self.assertIn("padding: 4px", result)
        self.assertIn("margin: 4px", result)
        self.assertIn("transition: all 0.2s ease", result)
        self.assertIn("box-shadow:", result)

    def test_invalid_type(self):
        # Test that invalid type raises an error
        with self.assertRaises(KeyError):
            apply_component_highlight("invalid", "<div>Test</div>", "Test")  # type: ignore
