import unittest
import collections

import numpy as np

from sympathy.api import table
import sylib.calculator.plugins as plugins
import sylib.calculator.calculator_model as models


class TestLogics(unittest.TestCase):
    """Test class that tests Logic operators and functions."""

    def setUp(self):
        self.longMessage = True

    def test_nand_index_array_constants(self):
        """
        Test :func:`NAND` with one index array and a constant.
        """
        signals = {"in_arr": np.ones(10)}
        expected = np.ones(10)

        out_arr = calc_wrapper("ca.nand(${in_arr}, 0)", signals)
        assert (out_arr == expected).all()
        out_arr = calc_wrapper("ca.nand(${in_arr}, False)", signals)
        assert (out_arr == expected).all()

        expected = np.zeros(10)
        out_arr = calc_wrapper("ca.nand(${in_arr}, 1)", signals)
        assert (out_arr == expected).all()
        out_arr = calc_wrapper("ca.nand(${in_arr}, True)", signals)
        assert (out_arr == expected).all()

    def test_nand_index_arrays(self):
        """
        Test :func:`NAND` with two index arrays of same length.
        """

        signals = {"in_arr": np.ones(10)}
        expected = np.zeros(10)
        out_arr = calc_wrapper("ca.nand(${in_arr}, ${in_arr})", signals)
        assert (out_arr == expected).all()

        signals = {"in_arr": np.ones(10),
                   "value": np.zeros(10)}
        expected = signals["in_arr"]
        out_arr = calc_wrapper("ca.nand(${in_arr}, ${value})", signals)
        assert (out_arr == expected).all()

        signals = {"in_arr": np.array([1, 1, 1, 0, 0, 0]),
                   "value": np.array([0, 0, 1, 0, 0, 1])}
        expected = np.array([1, 1, 0, 1, 1, 1])
        out_arr = calc_wrapper("ca.nand(${in_arr}, ${value})", signals)
        assert (out_arr == expected).all()

    def test_nor_index_array_constants(self):
        """
        Test :func:`NOR` with one index array and a constant.
        """
        signals = {"in_arr": np.ones(10)}
        expected = np.zeros(10)
        out_arr = calc_wrapper("ca.nor(${in_arr}, 0)", signals)
        assert (out_arr == expected).all()

        out_arr = calc_wrapper("ca.nor(${in_arr}, False)", signals)
        assert (out_arr == expected).all()

        out_arr = calc_wrapper("ca.nor(${in_arr}, 1)", signals)
        assert (out_arr == expected).all()

        out_arr = calc_wrapper("ca.nor(${in_arr}, True)", signals)
        assert (out_arr == expected).all()

        signals = {"in_arr": np.array([1, 1, 1, 0, 0, 0])}
        expected = np.array([0, 0, 0, 1, 1, 1])
        out_arr = calc_wrapper("ca.nor(${in_arr}, 0)", signals)
        assert (out_arr == expected).all()

        expected = np.zeros(6)
        out_arr = calc_wrapper("ca.nor(${in_arr}, 1)", signals)
        assert (out_arr == expected).all()

    def test_nor_index_arrays(self):
        """
        Test :func:`NOR` with two index arrays of same length.
        """

        signals = {"in_arr": np.ones(10)}
        expected = np.zeros(10)
        out_arr = calc_wrapper("ca.nor(${in_arr}, ${in_arr})", signals)
        assert (out_arr == expected).all()

        signals['value'] = np.zeros(10)
        out_arr = calc_wrapper("ca.nor(${in_arr}, ${value})", signals)
        assert (out_arr == expected).all()

        signals = {"in_arr": np.array([1, 1, 1, 0, 0, 0]),
                   "value": np.array([0, 0, 1, 0, 0, 1])}
        expected = np.array([0, 0, 0, 1, 1, 0])
        out_arr = calc_wrapper("ca.nor(${in_arr}, ${value})", signals)
        assert (out_arr == expected).all()


class TestEventDetection(unittest.TestCase):
    """Test class that tests Event detection functions."""
    def test_changed_simple(self):
        """Test :func:`changed` with np.array and a number."""

        in_arr = np.ones(10)
        signals = {"in_arr": in_arr}
        expected = np.zeros(10)
        out_arr = calc_wrapper("ca.changed(${in_arr})", signals)
        assert (out_arr == expected).all()

        in_arr = np.array([1, 0, 1, 0, 0, 1, 1])
        signals = {"in_arr": in_arr}
        expected = np.array([0, 1, 1, 1, 0, 1, 0])
        out_arr = calc_wrapper("ca.changed(${in_arr})", signals)
        assert (out_arr == expected).all()

        in_arr = np.array([4, 0, 5, 0, 0, 3, 1])
        signals = {"in_arr": in_arr}
        expected = np.array([0, 1, 1, 1, 0, 1, 1])
        out_arr = calc_wrapper("ca.changed(${in_arr})", signals)
        assert (out_arr == expected).all()

    def test_changed_negative_value(self):
        """Test :func:`changed` with np.array and a negative number."""

        in_arr = np.array([2, 0, 2, 0, 0, 2, 2])
        expected = np.array([0, 1, 1, 1, 0, 1, 0])
        signals = {"in_arr": in_arr}
        out_arr = calc_wrapper("ca.changed(${in_arr})", signals)
        assert (out_arr == expected).all()

    def test_changed_up_simple(self):
        """Test :func:`changed_up` with np.array and a number."""

        in_arr = np.ones(10)
        expected = np.zeros(10)
        signals = {"in_arr": in_arr}
        out_arr = calc_wrapper("ca.changed_up(${in_arr})", signals)
        assert (out_arr == expected).all()

        in_arr = np.array([1, 0, 1, 0, 0, 1, 1])
        expected = np.array([0, 0, 1, 0, 0, 1, 0])
        signals = {"in_arr": in_arr}
        out_arr = calc_wrapper("ca.changed_up(${in_arr})", signals)
        assert (out_arr == expected).all()

        in_arr = np.array([4, 0, 5, 0, 0, 3, 1])
        expected = np.array([0, 0, 1, 0, 0, 1, 0])
        signals = {"in_arr": in_arr}
        out_arr = calc_wrapper("ca.changed_up(${in_arr})", signals)
        assert (out_arr == expected).all()

        in_arr =   np.array([1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1])
        expected = np.array([0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0])
        signals = {"in_arr": in_arr}
        out_arr = calc_wrapper("ca.changed_up(${in_arr})", signals)
        assert (out_arr == expected).all()

    def test_changed_down_simple(self):
        """Test :func:`changed_down` with np.array and a number."""

        in_arr = np.ones(10)
        expected = np.zeros(10)
        signals = {"in_arr": in_arr}
        out_arr = calc_wrapper("ca.changed_down(${in_arr})", signals)
        assert (out_arr == expected).all()

        in_arr = np.ones(10)
        expected = np.zeros(10)
        signals = {"in_arr": in_arr}
        out_arr = calc_wrapper("ca.changed_down(${in_arr})", signals)
        assert (out_arr == expected).all()

        in_arr = np.array([1, 0, 1, 0, 0, 1, 1])
        expected = np.array([0, 1, 0, 1, 0, 0, 0])
        signals = {"in_arr": in_arr}
        out_arr = calc_wrapper("ca.changed_down(${in_arr})", signals)
        assert (out_arr == expected).all()

        in_arr = np.array([4, 0, 5, 0, 0, 3, 1])
        expected = np.array([0, 1, 0, 1, 0, 0, 1])
        signals = {"in_arr": in_arr}
        out_arr = calc_wrapper("ca.changed_down(${in_arr})", signals)
        assert (out_arr == expected).all()


def calc_wrapper(line, in_dict=None, extra_globals=None):
    """Simple wrapper around models.python_calculator."""
    in_table = table.File()
    if in_dict:
        for k, v in in_dict.iteritems():
            in_table.set_column_from_array(k, v)

    output = models.python_calculator(
        in_table, "${{a}} = {}".format(line), extra_globals or {})
    return output[0][1]


def eval_texts_calc_wrapper(line):
    """
    Wrapper around calc_wrapper supplying necessary data to run all eval texts
    in the standard library plugins.
    """
    # These signals are needed to run the functions as written in eval texts.
    signals = {
        'signal0': np.array([1, 1, 1, 0, 0]),
        'signal1': np.array([1, 1, 1, 0, 0]),
        'time': np.array([0, 1, 2, 3, 4])}

    # These variable names are needed to run the functions as written in
    # eval texts.
    extra_globals = {
        'value': 1,
        'shift_value': 1,
        'window_size': 3,
        'min_length': 1,
        'max_length': 2,
        'from_value': 1,
        'to_value': 0,
        'reset_array': np.array([False, True, False, True, False])}

    return calc_wrapper(line, signals, extra_globals)


def walk_gui_dict(gui_dict):
    """
    Traverse the dict/list gui_dict structure to find all eval texts yielding
    one test per eval text.
    """
    if isinstance(gui_dict, collections.Mapping):
        for value in gui_dict.values():
            for test in walk_gui_dict(value):
                yield test
    elif isinstance(gui_dict, collections.Iterable):
        for value in gui_dict:
            line = value[1]
            yield eval_texts_calc_wrapper, line
    else:
        raise TypeError("gui_dict() should return Mapping or Iterable. "
                        "Got {} instead.".format(type(gui_dict)))


def test_all_eval_strings():
    """Test that all plugin eval texts can be evaluated."""
    for plugin in plugins.available_plugins('python'):
        gui_dict = plugin.gui_dict()
        for test in walk_gui_dict(gui_dict):
            yield test


def test_enable():
    """"Test original requirements on some functions in ca."""

    def check_mask(i, eval_string):
        # Prints will be suppressed if test succeeds
        output = calc_wrapper(eval_string, signals)
        assert (output == result_rows[i]).all()

    signals = {'signal':
        np.array([4,4,4,4,4,0,0,0,0,0,0,4,4,4,4,4,0,0,1,2,3,1,1,1,1,2,2,1,0,0])}
    result_rows = [
        np.array([0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,1,1,0]).astype(bool),  # 0
        np.array([0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0]).astype(bool),  # 1
        np.array([0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0]).astype(bool),  # 2
        np.array([0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,1,0,1,1,1,1,0,0,0,1,0,1,1,0]).astype(bool),  # 3
        np.array([0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,1,1,1,0,0,0,0,1,0,0,0,0]).astype(bool),  # 4
        np.array([0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1,0,0,0,0,0,1,1,0]).astype(bool),  # 5
        np.array([0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,1,0,0,0,0,1,1,0,0,0]).astype(bool),  # 6
        np.array([0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,1,1,0,0,0,1,1,1,1,0,0,0,0,0]).astype(bool),  # 7
        np.array([0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]).astype(bool),  # 8
        np.array([0,0,0,0,0,1,1,1,1,1,1,1,1,1,0,0,1,1,1,1,1,0,0,0,0,0,0,0,1,1]).astype(bool)]  # 9

    check_mask(0, "ca.shift_array(${signal} == 0, -1)")
    check_mask(1, "ca.first(${signal} == 1)")
    check_mask(2, "ca.last(${signal} == 1)")
    check_mask(3, "ca.changed(${signal})")
    check_mask(4, "ca.changed_up(${signal})")
    check_mask(5, "ca.changed_down(${signal})")
    check_mask(6, "ca.local_max(${signal})")
    check_mask(7, "ca.local_min(${signal})")
    check_mask(8, "ca.shift_seq_start(${signal} == 0, 3)")
    check_mask(9, "ca.shift_seq_end(${signal} == 0, 3)")
