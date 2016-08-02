from sympathy.api.nodeconfig import LibraryTags, TagType, GroupTagType


class SylibLibraryTags(LibraryTags):
    class_tags = (
        GroupTagType(
            'Root',
            # Input group.
            (GroupTagType(
                'Input',
                (TagType('Import',
                         'Import external data from files or databases.'),
                 TagType('Generate',
                         'Generate data'))),

             # Export group.
             GroupTagType(
                'Output',
                (TagType('Export',
                         'Export data to external files or databases'),)),

             # Data Processing.
             GroupTagType(
                'DataProcessing',
                (TagType('Calculate',
                         'Calculate data based on input'),
                 TagType('Convert',
                         'Convert between internal datatypes'),
                 TagType('List',
                         'List data operations'),
                 TagType('Tuple',
                         'Tuple data operations'),
                 TagType('Index',
                         'Index data operations'),
                 TagType('Select',
                         'Select data parts'),
                 TagType('Transform',
                         'Transform structure',
                         name='Structure'),
                 TagType('TransformData',
                         'Transform data',
                         name='Transform'),
                 TagType('TransformMeta',
                         'Transform meta',
                         name='Meta')),

                name='Data Processing'),

             # Visual group.
             GroupTagType(
                 'Visual',
                 (TagType('Figure',
                          'Figure operations'),
                  TagType('Plot',
                          'Plot operations'),
                  TagType('Report',
                          'Report generating operations'))),

             # Analysis group.
             GroupTagType(
                 'Analysis',
                 (TagType('Statistic',
                          'Statistical data operations'),
                  TagType('SignalProcessing',
                          'Signal processing data operations',
                          name='Signal Processing'))),

             # Disk group.
             GroupTagType(
                'Disk',
                (TagType('File',
                         'File processing data operations'),)),

             # Example group.
             GroupTagType(
                 'Example',
                 (TagType('NodeWriting',
                          'Example nodes demonstrating different aspects of '
                          'node writing',
                          name='Node writing'),
                  TagType('Legacy',
                          'Example nodes from before Sympathy 1.0'),
                  TagType('Misc',
                          'Miscellaneous examples'))),

             # Hidden group.
             GroupTagType(
                 'Hidden',
                 (TagType('Deprecated',
                          'Deprecated nodes (will be removed)'),
                  TagType('Egg',
                          'Easter egg nodes')))
             )))

    def __init__(self):
        super(SylibLibraryTags, self).__init__()
        self._root = self.class_tags
