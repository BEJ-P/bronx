# -*- coding: utf-8 -*-

"""
Compatibility for some of the features of the itertools modules.

The pairwise function was introduced with Python3.10, we provide here a close approximation.
The real thing is used from 3.10 and on.
"""
import sys
import itertools

if sys.version_info.major == 3 and sys.version_info.major < 10:

    def pairwise(iterable):
        """Return successive overlapping pairs taken from the input iterable.

        >>> list(pairwise([1, 2, 3, 4]))
        [(1, 2), (2, 3), (3, 4)]

        >>> list(pairwise([1, ])) == list(pairwise([])) == []
        True
        """
        a, b = itertools.tee(iterable)
        next(b, None)
        return zip(a, b)

else:

    pairwise = itertools.pairwise
