import os
from sympathy.api import exporters
from sympathy.api.exceptions import sywarn


class TableExporterAccessManager(exporters.base.ExporterAccessManagerBase):
    pass


class TableDataExporterBase(exporters.base.TableDataExporterBase):
    access_manager = TableExporterAccessManager

    def create_filenames(self, node_context_input, filename):
        """
        Base implementation of create_filenames.
        Please override for custom behavior.
        """
        if not self.file_based():
            return exporters.base.inf_filename_gen('-')

        elif ('table_names' in self._custom_parameter_root and
                self._custom_parameter_root['table_names'].value):
            ext = self._custom_parameter_root['filename_extension'].value
            if ext != '':
                ext = '{}{}'.format(os.path.extsep, ext)
            try:
                tablelist = node_context_input['port0']
                filenames = [u'{}{}'.format(
                    t.get_name(), ext) for t in tablelist
                    if t.get_name() is not None]

                if len(set(filenames)) == len(tablelist):
                    return (filename for filename in filenames)
                else:
                    sywarn(
                        'The Tables in the incoming list do not '
                        'have unique names. The table names are '
                        'therefore not used as filenames.')
            except (IOError, OSError):
                    sywarn('Problem opening input data')

        filename_extension = self._custom_parameter_root[
            'filename_extension'].value
        return exporters.base.inf_filename_gen(filename, filename_extension)
