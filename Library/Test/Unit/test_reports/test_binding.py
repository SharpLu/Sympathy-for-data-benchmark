import unittest
from sylib.report import binding


class TestBindingHooks(unittest.TestCase):
    def setUp(self):
        self.result = None
        self.base_property = binding.PropertyWrapper(lambda: self.result,
                                                     self.base_setter)
        self.base_property_initial_setter = self.base_property.set
        self.binding_context = binding.BindingContext()
        self.hook1 = binding.create_and_apply_hook(
            self.base_property, self.binding_context)
        self.hook2 = binding.create_and_apply_hook(
            self.base_property, self.binding_context)
        self.hook3 = binding.create_and_apply_hook(
            self.base_property, self.binding_context)

    def base_setter(self, x):
        self.result = x

    def test_hook_chain(self):
        self.assertIs(self.result, None)
        self.hook3(0)
        self.assertEqual(self.result, 0)

    def test_remove_hook1(self):
        self.assertEqual(self.base_property.set, self.hook3)
        binding.remove_hook(self.hook1)
        self.assertEqual(self.base_property.set, self.hook3)
        self.assertEqual(self.hook3.previous_setter, self.hook2)
        self.assertEqual(self.hook2.previous_setter,
                         self.base_property_initial_setter)
        self.assertIs(self.result, None)
        self.hook3(0)
        self.assertEqual(self.result, 0)

    def test_remove_hook2(self):
        self.assertEqual(self.base_property.set, self.hook3)
        binding.remove_hook(self.hook2)
        self.assertEqual(self.base_property.set, self.hook3)
        self.assertEqual(self.hook3.previous_setter, self.hook1)
        self.assertEqual(self.hook1.previous_setter,
                         self.base_property_initial_setter)
        self.assertIs(self.result, None)
        self.hook3(0)
        self.assertEqual(self.result, 0)

    def test_remove_hook3(self):
        self.assertEqual(self.base_property.set, self.hook3)
        binding.remove_hook(self.hook3)
        self.assertEqual(self.base_property.set, self.hook2)
        self.assertEqual(self.hook2.previous_setter, self.hook1)
        self.assertEqual(self.hook1.previous_setter,
                         self.base_property_initial_setter)
        self.assertIs(self.result, None)
        self.hook2(0)
        self.assertEqual(self.result, 0)
