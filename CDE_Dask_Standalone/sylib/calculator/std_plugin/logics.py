# Copyright (c) 2013, System Engineering Software Society
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the System Engineering Software Society nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.
# IN NO EVENT SHALL SYSTEM ENGINEERING SOFTWARE SOCIETY BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import inspect
from itertools import izip

import numpy as np

from sylib.calculator import plugins


def find_sequences_indices(mask):
    """Return iterator with tuples of start and end indices for all sequences
    of True values in mask.

    Parameters
    ----------
    mask : np.ndarray
        The mask the function should be performed on.

    Returns
    -------
    tuples
        Iterator with a tuple of start and end indices for each sequences of
        True values in the input.

     Examples
    --------
    >>> mask = np.array([False, True, True, False])
    >>> list(_sequences(mask))
    [(1, 3)]
    >>> mask = np.array([True, False, False, True])
    >>> list(_sequences(mask))
    [(0, 1), (3, 4)]
    >>> mask = np.ones((4,), dtype=bool)
    >>> list(_sequences(mask))
    [(0, 4)]
    >>> mask = np.zeros((4,), dtype=bool)
    >>> list(_sequences(mask))
    []
    """
    if not np.any(mask):
        # There are no sequences in this mask
        return izip([], [])

    start_indices = np.flatnonzero(
        np.ediff1d(mask.astype(int), to_begin=0) == 1)
    end_indices = np.flatnonzero(
        np.ediff1d(mask.astype(int), to_begin=0) == -1)

    # If the mask starts or ends with a True value this needs to be handled
    # separately:
    if start_indices.size == 0 or end_indices[0] < start_indices[0]:
        start_indices = np.insert(start_indices, 0, 0)
    if end_indices.size == 0 or start_indices[-1] > end_indices[-1]:
        end_indices = np.append(end_indices, len(mask))
    return izip(start_indices, end_indices)


class Logics(object):
    @staticmethod
    def first(mask):
        """Return a new array which is True only at the very first position
        where mask was True.

        Parameters
        ----------
        mask : array_like
            The array the function should be performed on.

        Returns
        -------
        np.array
            An array with the same length and dtype as mask.
        """

        newmask = np.zeros_like(mask)
        indices = np.flatnonzero(mask)
        if len(indices):
            newmask[indices[0]] = True
            return newmask
        else:
            return newmask

    @staticmethod
    def last(mask):
        """Return a new array which is True only at the very last position
        where mask was True.

        Parameters
        ----------
        mask: array_like
            The array the function should be performed on.

        Returns
        -------
        np.array
            An array with the same length and dtype as mask.
        """

        newmask = np.zeros_like(mask)
        indices = np.flatnonzero(mask)
        if len(indices):
            newmask[indices[-1]] = True
            return newmask
        else:
            return newmask

    @staticmethod
    def shift_array(mask, shift_value):
        """Return a new mask with values shifted by shift_value
        compared to mask. shift_value can be any integer.

        mask : array_like
            A numpy array with booleans.
        shift_value : int
            The number of positions that mask should be shifted by.

        Returns
        -------
        np.array
            An array of booleans with the same length as mask.
        """

        new_values = np.zeros((abs(shift_value),), dtype=bool)
        if shift_value == 0:
            return mask
        elif shift_value > 0:
            return np.insert(mask[:-shift_value], 0, new_values)
        else:
            return np.append(mask[abs(shift_value):], new_values)

    @staticmethod
    def shift_seq_start(mask, shift_value):
        """Return a mask whose sequences of True values start shift_value
        values later than the sequences in mask, but end on the same value as
        the original sequence in mask. As a consequence, if shift_value is
        positive, sequences shorter than or equal to shift_value will disappear.

        mask : array_like
            A numpy array with booleans.
        shift_value : int
            The number of positions that mask should be shifted by.

        Returns
        -------
        np.array
            An array with the same length and dtype as mask.

        Examples
        --------
        >>> mask = np.array(
            [True, True, False, False, True, True, True, False])
        >>> shift_seq_start(mask, 2)
        array([False, False, False, False, False, False,  True, False], dtype=bool)
        >>> shift_seq_start(mask, -1)
        array([True, True, False, True, True, True, True, False], dtype=bool)
        """

        newmask = np.zeros_like(mask)
        for start_index, end_index in find_sequences_indices(mask):
            # Protection needed when shift_value is a big enough negative value
            new_start_index = max(start_index + shift_value, 0)
            # This doesn't do anything if new_start_index > end_index
            newmask[new_start_index:end_index] = True
        return newmask

    @staticmethod
    def shift_seq_end(mask, shift_value):
        """Return a mask whose sequences of True values start on the same value
        as the original sequence in mask, but end shift_value values later than
        the sequences in mask. As a consequence, if shift_value is negative,
        sequences shorter than or equal to shift_value will disappear.

        Parameters
        ----------
        mask : array_like
            A numpy array with booleans.
        shift_value : int
            The number of positions that mask should be shifted by.

        Returns
        -------
        np.array
            An array with the same length and dtype as mask.

        Examples
        --------
        >>> mask = np.array([True, False, False, False, True, True, False])
        >>> shift_seq_end(mask, 2)
        array([True, True, True, False, True, True, True], dtype=bool)
        >>> shift_seq_end(mask, -1)
        array([False, False, False, False, True, False, False], dtype=bool)
        """

        newmask = np.zeros_like(mask)
        for start_index, end_index in find_sequences_indices(mask):
            # Protection needed when shift_value is a big enough negative value
            if end_index + shift_value >= 0:
                # This doesn't do anything if
                # start_index > end_index + shift_value
                newmask[start_index:end_index + shift_value] = True
        return newmask


GUI_DICT = {
    "Logic functions": [
        ("Last", "ca.last(${signal0})", inspect.getdoc(Logics.last)),
        ("First", "ca.first(${signal0})", inspect.getdoc(Logics.first)),
        ("Shift array", "ca.shift_array(${signal0}, shift_value)",
         inspect.getdoc(Logics.shift_array)),
        ("Shift sequence start",
         "ca.shift_seq_start(${signal0}, shift_value)",
         inspect.getdoc(Logics.shift_seq_start)),
        ("Shift sequence end", "ca.shift_seq_end(${signal0}, shift_value)",
         inspect.getdoc(Logics.shift_seq_end)),
    ]
}
