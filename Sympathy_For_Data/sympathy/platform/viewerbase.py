from PySide import QtGui


class ViewerBase(QtGui.QWidget):
    def __init__(self, parent=None):
        super(ViewerBase, self).__init__(parent)

    def update_data(self, data):
        raise NotImplementedError('Not implemented in base class')

    def data(self):
        raise NotImplementedError('Not implemented in base class')

    def custom_menu_items(self):
        return []
