from sympathy.utils.components import get_components


class ICalcPlugin(object):
    """Interface for calculator plugins."""

    WEIGHT = 10000

    @staticmethod
    def gui_dict():
        """Return a dictionary with functions that will be shown in the
        configuration gui for the calculator node.
        """
        return {}

    @staticmethod
    def globals_dict():
        """Return a dictionary that will be added to the globals dictionary
        when executing calculations.
        """
        return {}


class MatlabCalcPlugin(object):
    """Interface for calculator plugins."""

    WEIGHT = 10000

    @staticmethod
    def gui_dict():
        """Return a dictionary with functions that will be shown in the
        configuration gui for the calculator node.
        """
        return {}

    @staticmethod
    def globals_dict():
        """Return a dictionary that will be added to the globals dictionary
        when executing calculations.
        """
        return {}


def available_plugins(backend='python'):
    """Return all available plugins derived for a specific backend."""
    plugin_classes = {'python': ICalcPlugin,
                      'matlab': MatlabCalcPlugin}
    return get_components('plugin_*.py', plugin_classes[backend])
