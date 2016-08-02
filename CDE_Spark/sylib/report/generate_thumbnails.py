import json
import sys


THUMBNAIL_WIDTH = 64


def main():
    """This function should always be run in its own process to avoid polluting
    the worker process with a QApplication.
    """
    (sys_path_json, template, data_filename, data_type) = sys.argv[1:]
    sys.path[:] = json.loads(sys_path_json)

    from sympathy.api import adaf, table
    from sympathy.api import qt
    from sylib.report import data_manager
    from sylib.report import models
    from sylib.report import binding
    from sylib.report import plugins
    QtGui = qt.QtGui
    QtCore = qt.QtCore

    def file_type(data_type):
        if data_type == 'adafs':
            return adaf.FileList
        elif data_type == 'tables':
            return table.FileList
        else:
            assert(False)

    # In this process it is safe to create a QApplication.
    app = QtGui.QApplication([])

    # Read the data from the transfer file.
    with file_type(data_type)(filename=data_filename, mode='r') as input_data:

        data_manager.init_data_source(input_data, data_type)
        model = models.Root(json.loads(template))
        backend = plugins.backend_modules['mpl'].backend
        binding_context = binding.BindingContext()
        factory = backend.ItemFactory(binding_context)
        page_models = model.find_all_nodes_with_class(models.Page)
        page_count = len(page_models)

        # Generate thumbnails.
        thumbnails = []
        if page_count > 0:
            for page_index, page_model in enumerate(page_models):
                page_widget = factory._create_page(page_model)
                QtGui.QApplication.processEvents()

                pixmap = QtGui.QPixmap.grabWidget(page_widget)
                pixmap = pixmap.scaledToWidth(THUMBNAIL_WIDTH,
                                              QtCore.Qt.SmoothTransformation)
                bytes = QtCore.QByteArray()
                buffer = QtCore.QBuffer(bytes)
                buffer.open(QtCore.QIODevice.WriteOnly)
                pixmap.save(buffer, 'PNG')
                buffer.close()
                thumbnails.append(unicode(bytes.toBase64()))
    print json.dumps(thumbnails)


if __name__ == '__main__':
    main()
