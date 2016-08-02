import os
from sympathy.api import qt as qt_compat
QtGui = qt_compat.import_module('QtGui') # noqa
from sympathy.api import node as synode
from sympathy.api import exporters


class ADAFExporterAccessManager(exporters.base.ExporterAccessManagerBase):
    pass


class ADAFDataExporterBase(exporters.base.ADAFDataExporterBase):
    access_manager = ADAFExporterAccessManager

    @classmethod
    def _create_filename_using_column(cls, parameter_root, adaf_file):
        column_name = parameter_root['column_as_name'].selected
        meta_value = adaf_file.meta[column_name].value()
        if meta_value is None:
            meta_value = adaf_file.meta[column_name].value()

        if len(meta_value) > 0:
            return meta_value[0]
        else:
            return None

    @classmethod
    def _create_filename_using_strategy(cls, parameter_root,
                                        node_context_input):
        selected_strategy_name = parameter_root['selected_strategy'].selected
        filename_wo_ext = None
        if selected_strategy_name == 'Source identifier as name':
            filename_wo_ext = node_context_input.source_id()
        elif selected_strategy_name == 'Column as name':
            filename_wo_ext = cls._create_filename_using_column(
                parameter_root, node_context_input)

        filename_extension = parameter_root['filename_extension'].value
        filename = u'{0}{1}{2}'.format(
            filename_wo_ext, os.path.extsep, filename_extension)
        return filename

    @classmethod
    def _create_filenames(cls, parameter_root, node_context_input, port_name):
        created_filenames = []
        try:
            input_list = node_context_input[port_name]
            for adaf_file in input_list:
                created_filenames.append(
                    cls._create_filename_using_strategy(
                        parameter_root, adaf_file))
        except IOError:
            pass
        return created_filenames

    def create_filenames(self, node_context_input, filename):
        """Return a list of filenames that will be exported to."""
        if not self.file_based():
            return super(exporters.base.TableDataExporterBase,
                         self).create_filenames()

        use_filename_strategy = self._custom_parameter_root[
            'use_filename_strategy'].value

        if use_filename_strategy:
            filenames = self._create_filenames(
                self._custom_parameter_root, node_context_input, 'port0')
            if filenames:
                return filenames
            else:
                return ['Cannot preview filenames']

        filename_extension = self._custom_parameter_root[
            'filename_extension'].value
        return exporters.base.inf_filename_gen(filename, filename_extension)


def get_column_from_adaf_list(node_context_input, port_name, group):
    input_list = node_context_input[port_name]
    if input_list.is_valid():
        adaf_file = []
        if len(input_list):
            adaf_file = input_list[0]
        try:
            return sorted(getattr(adaf_file, group).keys())
        except:
            return []
    else:
        return []


class FilenameStrategy(object):
    def __init__(self, name, widget):
        self._name = name
        self._widget = widget

    def name(self):
        return self._name

    def widget(self):
        return self._widget


class TabbedStrategyWidget(QtGui.QWidget):
    def __init__(self, parameter_root, filename_strategies=None, parent=None):
        super(TabbedStrategyWidget, self).__init__(parent)
        self._parameter_root = parameter_root

        self._filename_strategies = (
            [] if filename_strategies is None else filename_strategies)
        self._init_gui()

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        strategy_vlayout = QtGui.QVBoxLayout()
        self._strategy_groupbox = QtGui.QGroupBox("Strategy")
        self._strategy_groupbox.setLayout(strategy_vlayout)

        self._strategy_tabwidget = QtGui.QTabWidget()

        # Init GUI before the widgets are created
        self._pre_init_gui_from_parameters()

        self._use_filename_strategy_widget = (
            self._parameter_root['use_filename_strategy'].gui())

        self._strategy_widget = (
            self._parameter_root['selected_strategy'].gui())
        self._strategy_combobox = self._strategy_widget.editor().combobox()

        self._post_init_gui_from_parameters()

        vlayout.addWidget(self._use_filename_strategy_widget)
        strategy_vlayout.addWidget(self._strategy_widget)
        strategy_vlayout.addWidget(self._strategy_tabwidget)
        vlayout.addWidget(self._strategy_groupbox)
        self.setLayout(vlayout)

        self._use_filename_strategy_widget.stateChanged[int].connect(
            self._state_changed)
        self._strategy_combobox.currentIndexChanged[int].connect(
            self._strategy_combo_changed)
        self._strategy_tabwidget.currentChanged[int].connect(
            self._tab_changed)

    def _pre_init_gui_from_parameters(self):
        self._parameter_root['selected_strategy'].list = []
        for filename_strategy in self._filename_strategies:
            self.add_strategy(filename_strategy)

    def _post_init_gui_from_parameters(self):
        use_filename_strategy = (
            self._parameter_root['use_filename_strategy'].value)
        self._strategy_groupbox.setEnabled(use_filename_strategy)
        selected_strategy_name = (
            self._parameter_root['selected_strategy'].selected)
        index = self._strategy_combobox.findText(selected_strategy_name)
        if -1 == index:
            index = 0
        self._strategy_tabwidget.setCurrentIndex(index)

    def add_strategy(self, filename_strategy):
        self._parameter_root['selected_strategy'].list.append(
            filename_strategy.name())
        self._strategy_tabwidget.addTab(
            filename_strategy.widget(),
            filename_strategy.name())

    def _strategy_combo_changed(self, index):
        self._strategy_tabwidget.setCurrentIndex(index)

    def _tab_changed(self, index):
        self._strategy_combobox.setCurrentIndex(index)

    def _state_changed(self, state):
        self._strategy_groupbox.setEnabled(
            self._parameter_root['use_filename_strategy'].value)


class TabbedADAFDataExporterBase(ADAFDataExporterBase):
    def __init__(self, custom_parameter_root):
        super(TabbedADAFDataExporterBase, self).__init__(custom_parameter_root)

        if 'use_filename_strategy' not in custom_parameter_root:
            custom_parameter_root.set_boolean(
                "use_filename_strategy", label="Use filename strategy",
                description="Use a strategy to create the filename(s).")

        if 'selected_strategy' not in custom_parameter_root:
            custom_parameter_root.set_list(
                "selected_strategy",
                label="Selected strategy",
                description="The selected filename strategy.",
                editor=synode.Util.combo_editor().value())

        if 'use_column_as_name' not in custom_parameter_root:
            custom_parameter_root.set_boolean(
                "use_column_as_name", label="Use a column as name",
                description="Use a data column from meta or result as "
                            "the filename.")

        if 'column_as_name' not in custom_parameter_root:
            custom_parameter_root.set_list(
                "column_as_name",
                editor=synode.Util.combo_editor().value())


class TabbedDataExportWidget(QtGui.QWidget):
    def __init__(self, parameter_root, node_context_input):
        super(TabbedDataExportWidget, self).__init__()
        self._parameter_root = parameter_root
        self._node_context_input = node_context_input
        self._filename_strategies = []
        self._init_parameters()
        self._init_gui()

    def _init_parameters(self):
        # Init GUI before the widgets are created
        self._init_gui_from_parameters()

        self._use_column_as_name_widget = (
            self._parameter_root['use_column_as_name'].gui())
        self._column_as_name_widget = (
            self._parameter_root['column_as_name'].gui())

        self._filename_strategies.append(
            FilenameStrategy(
                "Source identifier as name",
                QtGui.QWidget()))

        self._filename_strategies.append(
            FilenameStrategy(
                "Column as name",
                self._column_as_name_widget))

        self._tabbed_strategy_widget = TabbedStrategyWidget(
            self._parameter_root, self._filename_strategies)

    def _init_gui(self):
        vlayout = QtGui.QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self._tabbed_strategy_widget)
        self.setLayout(vlayout)

    def _init_gui_from_parameters(self):
        meta_columns = get_column_from_adaf_list(
            self._node_context_input, 'port0', 'meta')
        value_names = self._parameter_root['column_as_name'].value_names[:]
        self._parameter_root['column_as_name'].list = (
            [name for name in value_names
             if name not in meta_columns] +
            meta_columns)
        self._parameter_root['column_as_name'].value_names = value_names
