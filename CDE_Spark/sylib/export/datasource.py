from sympathy.api import exporters
from sympathy.api.exceptions import sywarn, NoDataError


class DatasourceExporterAccessManager(
        exporters.base.ExporterAccessManagerBase):

    def create_filenames(self, parameter_root, node_context_input):
        try:
            if self._exporter.file_based():
                return self._exporter.create_filenames(
                    node_context_input)
            return self._exporter.create_filenames(node_context_input)
        except NoDataError:
            return []


class DatasourceDataExporterBase(exporters.base.DatasourceDataExporterBase):
    access_manager = DatasourceExporterAccessManager

    def warn_invalid(self, in_datasource):
        sywarn(u'{} is not a valid {} file'.format(
               in_datasource.decode_path(), self.EXPORTER_NAME))
