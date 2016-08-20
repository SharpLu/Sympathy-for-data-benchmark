from __future__ import (print_function, division, unicode_literals,
                        absolute_import)
from sympathy.api import fx_wrapper


class GenericPrintCalculation(fx_wrapper.FxWrapper):
    arg_types = ['<a>']

    def execute(self):
        # See the Table API description in the Help (under Data type
        # APIs) for more information on how to write functions.
        print('Forwarding arg: {}'.format(self.arg))
        self.res.source(self.arg)


class SingleSpamCalculation(fx_wrapper.FxWrapper):
    arg_types = ['table']

    def execute(self):
        # See the ADAF API description in the Help (under Data type
        # APIs) for more information on how to write functions.

        spam = self.arg.get_column_to_array('spam')

        # My super advanced calculation that totally couldn't be
        # done in the :ref:`Calculator` node:
        more_spam = spam + 1
        self.res.set_column_from_array('more spam', more_spam)
        print('more spam')
