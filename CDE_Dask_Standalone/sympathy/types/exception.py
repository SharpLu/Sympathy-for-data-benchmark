class WritebackError(AssertionError):
    pass


class WritebackReadOnlyError(WritebackError):
    pass


def assert_exc(pred, exc=AssertionError, msg=None):
    if not pred:
        if msg:
            raise exc(msg)
        else:
            raise exc
