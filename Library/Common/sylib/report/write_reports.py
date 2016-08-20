import os
import json
import sys


def main():
    """This function should always be run in its own process to avoid polluting
    the worker process with a QApplication.
    """
    (sys_path_json, template, signal_mapping, data_filename, data_type,
     file_format, save_path_json, prefix_json,
     input_filenames_json) = sys.argv[1:]
    sys.path[:] = json.loads(sys_path_json)
    input_filenames = json.loads(input_filenames_json)
    save_path = json.loads(save_path_json)
    prefix = json.loads(prefix_json)

    from sympathy.api import adaf, table
    from sympathy.api import qt
    from sylib.report import data_manager
    from sylib.report import models
    from sylib.report import binding
    from sylib.report import plugins
    QtGui = qt.QtGui

    def file_type(data_type):
        if data_type == 'adafs':
            return adaf.FileList
        elif data_type == 'tables':
            return table.FileList
        else:
            assert(False)

    def warn(msg):
        sys.stderr.write("__WARNING__ ({})\n".format(msg.encode('utf8')))

    def error(msg):
        sys.stderr.write("__ERROR__ ({})".format(msg.encode('utf8')))
        sys.exit()

    # In this process it is safe to create a QApplication.
    app = QtGui.QApplication([])

    # Extract all pages manually to get minimal size images for all pages.
    model = models.Root(json.loads(template))
    page_models = model.find_all_nodes_with_class(models.Page)
    page_count = len(page_models)

    # Create filenames for all pages.
    if input_filenames is None:
        if not save_path:
            error("Please specify a save path.")
        basenames = ['{}_{}.{}'.format(prefix, i, file_format)
                     for i in range(page_count)]
        input_filenames = [os.path.join(save_path, basename)
                           for basename in basenames]
    else:
        if len(input_filenames) < page_count:
            error("Not enough filenames.")
        elif len(input_filenames) > page_count:
            warn("Too many filenames.")

    # Read the data from the transfer file.
    with file_type(data_type)(filename=data_filename, mode='r') as input_data:

        data_manager.init_data_source(input_data, data_type)
        data_manager.data_source.set_signal_mapping(json.loads(signal_mapping))

        QtGui.QApplication.processEvents()

        # Extract widgets.
        backend = plugins.backend_modules['mpl'].backend
        binding_context = binding.BindingContext()
        factory = backend.ItemFactory(binding_context)
        page_widgets = [factory._create_page(m) for m in page_models]

        QtGui.QApplication.processEvents()

        # Write widgets to file.
        output_filenames = []
        for i, (page_widget, filename) in enumerate(
                zip(page_widgets, input_filenames)):
            try:
                if not os.path.exists(os.path.dirname(filename)):
                    os.makedirs(os.path.dirname(filename))
            except (OSError, IOError):
                error("Could not create output directory {}".format(
                    os.path.dirname(filename)))
            pixmap = QtGui.QPixmap.grabWidget(page_widget)
            successful = pixmap.save(filename, format=file_format)
            if not successful:
                error("Could not write to file {}".format(filename))
            output_filenames.append(filename)
    print json.dumps(output_filenames)


if __name__ == '__main__':
    main()
