from . import sybase
from . import exception as exc


def _int_index_guard(index):
    if not isinstance(index, int):
        raise TypeError(
            u'Only basic integer indexing is supported, not: "{}"'
            .format(index))


class sytuple(sybase.sygroup):
    def __init__(self, container_type, datasource=sybase.NULL_SOURCE):
        super(sytuple, self).__init__(container_type,
                                      datasource or sybase.NULL_SOURCE)
        self.content_types = []
        self._content_types = []

        for content_type in container_type:
            self.content_types.append(content_type)
            try:
                while True:
                    content_type = content_type.get()
            except AttributeError:
                self._content_types.append(content_type)

        self._cache = [None] * len(container_type)

    def __repr__(self):
        return str(self._cache)

    def __len__(self):
        return len(self._cache)

    def __iter__(self):
        for i in range(len(self._cache)):
            yield self.__getitem__(i)

    def __getitem__(self, index):
        _int_index_guard(index)

        value = self._cache[index]
        if value is None:
            content_type = self.content_types[index]
            try:
                # Read from datasource.
                source = self._datasource.read_with_type(
                    str(index), self._content_types[index])
            except KeyError:
                # Create content without datasource.
                value = self._factory.from_type(content_type)
            else:
                # Create content from datasource.
                source = source or sybase.NullSource
                value = self._factory.from_datasource(
                    source,
                    content_type)
            self._cache[index] = value
        return value

    def __setitem__(self, index, value):
        _int_index_guard(index)
        content_type = self.content_types[index]
        sybase.assert_type(
            self, value.container_type, content_type)
        self._cache[index] = value

    def __copy__(self):
        obj = super(sytuple, self).__copy__()
        obj.content_types = self.content_types
        obj._content_types = self._content_types
        obj._cache = list(self._cache)
        return obj

    def __deepcopy__(self, memo=None):
        obj = self.__copy__()
        obj._cache = [None if v is None else v.__deepcopy__()
                      for v in enumerate(self._cache)]
        return obj

    def update(self, other):
        sybase.assert_type(
            self._container_type, other._container_type)
        self._cache = []
        for i in range(len(other)):
            self._cache[i] = other._cache[i]

    def source(self, other):
        self.update(other.__deepcopy__())

    def writeback(self):
        super(sytuple, self).writeback()

    def _writeback(self, datasource, link=None):
        origin = self._datasource
        target = datasource
        exc.assert_exc(target.can_write, exc=exc.WritebackReadOnlyError)
        shares_origin = target.shares_origin(origin)

        if link:
            return False

        for index, value in (
                enumerate(self._cache) if shares_origin
                else enumerate([self.__getitem__(i)
                                for i in range(len(self._cache))])):
            key = str(index)
            if value is not None:
                if not value._writeback(target, key):
                    new_target = target.write_with_type(
                        key, value, self._content_types[index])
                    value._writeback(new_target)

        return True
