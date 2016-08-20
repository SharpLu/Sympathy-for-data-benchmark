from sympathy.api import fx_wrapper


class DropLastColumn(fx_wrapper.FxWrapper):
    arg_types = ['table']

    def execute(self):
        for column in self.arg.column_names()[:-1]:
            self.res.set_column_from_array(
                column, self.arg.get_column_to_array(column))
