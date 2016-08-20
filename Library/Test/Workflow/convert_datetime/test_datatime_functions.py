from sympathy.api import table_wrapper


class TesTDatetimeFormats(table_wrapper.TableWrapper):
    """
    Test if self.in_table is equivalent with self.extra_table. Test is
    performed to check the exportation of datetime to csv.
    """
    def execute(self):
        part_res = []
        for column in self.extra_table.column_names():
            ref_col = self.extra_table.get_column_to_array(column).tolist()
            try:
                in_col = self.in_table.get_column_to_array(column).tolist()
            except KeyError:
                raise KeyError(
                    'Incoming Table seem to lost a column along the way')

            part_res.append(
                all([in_value == ref_value for in_value, ref_value in zip(
                    in_col, ref_col)]))

        if not all(part_res):
            raise Exception(
                'Exportation of datetime object to csv was not performed '
                'correctly.')
