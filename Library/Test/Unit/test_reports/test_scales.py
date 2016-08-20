import unittest
import numpy as np
from sylib.report import scales


class TestScales(unittest.TestCase):
    def test_identity_scale(self):
        identity_scale = scales.IdentityScale()
        self.assertEqual(identity_scale(0.0), 0.0)
        self.assertEqual(identity_scale(1.0), 1.0)

        domain_list = [1, 2, 3]
        domain_np_array = np.array(domain_list)

        range_list = identity_scale(domain_list)
        range_np_array = identity_scale(domain_np_array)

        self.assertIsInstance(range_list, type(domain_list))
        self.assertIsInstance(range_np_array, type(range_np_array))

        # Ensure types are ok.
        self.assertListEqual(domain_list, range_list)
        self.assertItemsEqual(domain_np_array, range_np_array)

    def test_color_conversion(self):
        color_string = '#224466'

        color_tuple = scales.color_string_to_tuple(color_string)
        self.assertEqual(color_tuple[0], 0x22)
        self.assertEqual(color_tuple[1], 0x44)
        self.assertEqual(color_tuple[2], 0x66)

        new_color_string = scales.tuple_to_color_string(color_tuple)
        self.assertEqual(color_string, new_color_string)

        color1_string = '#ffffff'
        color2_string = '#000000'
        color1_tuple = scales.color_string_to_tuple(color1_string)
        color2_tuple = scales.color_string_to_tuple(color2_string)
        mid_color_tuple = scales.interpolate_color_tuples(
            color1_tuple, color2_tuple, 0.5)
        mid_color_string = scales.tuple_to_color_string(mid_color_tuple)
        self.assertEqual(mid_color_string, '#7f7f7f')

    def test_linear_scale(self):
        # Test numerics.
        linear_scale = scales.LinearScale([0, 1], [1, 2])

        self.assertEqual(linear_scale(0), 1)
        self.assertEqual(linear_scale(0.5), 1.5)
        self.assertEqual(linear_scale(1), 2)

        domain_values = [0, 0.5, 1]
        range_values = linear_scale(domain_values)

        self.assertItemsEqual(range_values, [1, 1.5, 2])

        # Test colors.
        linear_color_scale = scales.LinearScale([0, 1], ['#ff0000', '#0000ff'])

        self.assertEqual(linear_color_scale(0), '#ff0000')
        self.assertEqual(linear_color_scale(1), '#0000ff')
        self.assertEqual(linear_color_scale(0.5), '#7f007f')

    def test_ordinal_scale(self):
        dom = ('a', 'b', 20)
        rng = (1, 2, 3)
        ordinal_scale = scales.OrdinalScale(dom, rng)

        for d, r in zip(dom, rng):
            self.assertEqual(ordinal_scale(d), r)
