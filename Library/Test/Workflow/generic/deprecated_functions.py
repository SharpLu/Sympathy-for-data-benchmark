from sympathy.api import adaf_wrapper, table_wrapper


class ExtraTable(table_wrapper.TableWrapper):
    def execute(self):
        print 'in table', self.in_table
        print 'out table', self.out_table
        print 'extra table', self.extra_table


class ExtraTables(table_wrapper.TablesWrapper):
    def execute(self):
        print 'in table list', self.in_table_list
        print 'out table list', self.out_table_list
        print 'extra', self.extra_table


class ExtraADAF(adaf_wrapper.ADAFWrapper):
    def execute(self):
        print 'in adaf', self.in_adaf
        print 'out adaf', self.out_adaf
        print 'extra table', self.extra_table


class ExtraADAFs(adaf_wrapper.ADAFsWrapper):
    def execute(self):
        print 'in adaf list', self.in_adaf_list
        print 'out', self.out_adaf_list
        print 'extra', self.extra_table
