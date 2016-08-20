import unittest
import sys
if sys.platform == 'win32':
    import ntpath as pathmod
else:
    import os.path as pathmod

from sylib.report import plugins


class TestPluginLoader(unittest.TestCase):
    def test_plugin_loader(self):
        layer_dict = plugins.backend_modules
        # Check names of things.
        # for k, v in layer_dict.iteritems():
        #     self.assertEqual(k, pathmod.basename(v.filename))
        #     self.assertEqual(k, v.fullname)

        # # Check module creation.
        # for k in layer_dict:
        #     module = layer_dict[k]
        #     self.assertEqual(module.__name__, k)

