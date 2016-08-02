import inspect

import numpy as np


def _between(start_mask, end_mask):
    """Return a new mask which is True in the smallest possible half open
    intervals from when start_mask is True up until just before the next time
    that end_mask becomes True.

    Parameters
    ----------
    start_mask : np.array
        The start mask
    end_mask : np.array
        The end mask

    Returns
    -------
    np.array
        An index array with booleans with the same length
        as start_mask and end_mask.

    Raises
    ------
    ValueError
        If start_mask and end_mask is not of same shape.

    Examples
    --------
    >>> start_mask = np.array(
    ...     [1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0], dtype=bool)
    >>> end_mask = np.array(
    ...     [0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1], dtype=bool)
    >>> result = np.array(
    ...     [0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0], dtype=bool)
    >>> np.all(_between(start_mask, end_mask) == result)
    True
    """

    if start_mask.shape != end_mask.shape:
        raise ValueError("start_mask and end_mask must have the same shape. "
                         "{} != {}".format(start_mask.shape, end_mask.shape))

    start_indices = np.flatnonzero(start_mask)
    end_indices = np.flatnonzero(end_mask)
    mask = np.zeros_like(start_mask)

    next_start_indices = np.append(start_indices[1:], len(start_mask))
    for start_index, next_start_index in zip(
            start_indices, next_start_indices):

        # Find corresponding end_index
        possible_end_indices = end_indices[end_indices > start_index]
        if len(possible_end_indices):
            end_index = possible_end_indices[0]
        else:
            # No end_index could be found so there are no more intervals
            break

        # Only set True values in mask if this is the smallest possible
        # interval
        if next_start_index < end_index:
            continue
        else:
            mask[start_index:end_index] = True

    return mask


class EventDetection(object):
    """Container class for event detection functions."""
    @staticmethod
    def changed(signal):
        """Return a boolean array which is True at each position where signal
        is different than at the previous position. The first element in the
        returned array is always False.

        Parameters
        ----------
        signal : np.array
            The array the function should be performed on.

        Returns
        -------
        np.array
            An array of booleans with the same length as signal.
        """
        return np.insert(signal[:-1] != signal[1:], 0, False)

    @staticmethod
    def changed_up(signal):
        """Return a boolean array which is True at each position where signal
        is greater than at the previous position. The first element in the
        returned array is always False.

        Parameters
        ----------
        signal : np.array
            The array the function should be performed on.

        Returns
        -------
        np.array
            An array of booleans with the same length as signal.
        """
        if signal.dtype.kind == 'b':
            signal = signal.astype(float)
        return np.ediff1d(signal, to_begin=0) > 0

    @staticmethod
    def changed_down(signal):
        """Return a boolean array which is True where ``signal`` is less than at
        the previous position. The first element in the returned array is
        always ``False``.

        Parameters
        ----------
        signal : np.array
            The array the function should be performed on.

        Returns
        -------
        np.array
            An index array with booleans with the same length as in_arr.
        """
        if signal.dtype.kind == 'b':
            signal = signal.astype(float)
        return np.ediff1d(signal, to_begin=0) < 0

    @staticmethod
    def local_max(signal):
        """Return a boolean array which is True at each local maximum in
        signal, i.e. between an increase and a decrease in signal. Maxima at
        signal boundaries aren't included.

        Parameters
        ----------
        signal : np.array
            The signal the function should be performed on.

        Returns
        -------
        np.array
            An array of booleans with the same length as signal.

        Examples
        --------
        >>> signal = np.array([1, 0, 1, 0, 1, 1, 2, 0])
        >>> peaks = np.array(
        ...     [False, False, True, False, False, False, True, False])
        >>> np.all(local_max(signal) == peaks)
        True
        """

        return _between(EventDetection.changed_up(signal),
                        EventDetection.changed_down(signal))

    @staticmethod
    def local_min(signal):
        """Return a boolean array which is True at each local minimum in
        signal, i.e. between a decrease and an increase in signal. Minima at
        signal boundaries aren't included.

        Parameters
        ----------
        signal : np.array
            The signal the function should be performed on.

        Returns
        -------
        np.array
            An array of booleans with the same length as signal.

        Examples
        --------
        >>> signal = np.array([1, 0, 1, 0, -1, -1, -2, 0])
        >>> peaks = np.array(
        ...     [False, True, False, False, False, False, True, False])
        >>> np.all(local_min(signal) == peaks)
        True
        """

        return _between(EventDetection.changed_down(signal),
                        EventDetection.changed_up(signal))


GUI_DICT = {
    "Event detection": [
        ("Changed", "ca.changed(${signal0})",
         inspect.getdoc(EventDetection.changed)),
        ("Changed up", "ca.changed_up(${signal0})",
         inspect.getdoc(EventDetection.changed_up)),
        ("Changed down", "ca.changed_down(${signal0})",
         inspect.getdoc(EventDetection.changed_down)),
        ("Local min", "ca.local_min(${signal0})",
         inspect.getdoc(EventDetection.local_min)),
        ("Local max", "ca.local_max(${signal0})",
         inspect.getdoc(EventDetection.local_max)),
        ("Global min", "${signal0} == ${signal0}.min()",
         "Return a boolean array which is True when signal is at its minimum value."),
        ("Global max", "${signal0} == ${signal0}.max()",
         "Return a boolean array which is True when signal is at its maximum value."),
    ]
}
