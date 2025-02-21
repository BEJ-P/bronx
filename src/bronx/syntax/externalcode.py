# -*- coding: utf-8 -*-

"""
A handy class that checks that an external code import worked properly.

If not, a decorator is provided to disable portions of code.

Example of a simple use::

    from bronx.syntax.externalcode import ExternalCodeImportChecker

    echecker = ExternalCodeImportChecker('anypackage')
    with echecker:
        import anypackage

    print('Did it work ? {!s}'.format(echecker.is_available()))

    @echecker.disabled_if_unavailable
    def my_function_based_on_anypackage()
        return anypackage.sayhi()

    @echecker.disabled_if_unavailable
    class MyClassBasedOnAnypackage(object)

        def sayhi(self)
            return anypackage.sayhi()

    # A call to my_function_based_on_anypackage or any attempt to create a
    # MyClassBasedOnAnypackage object will lead to a ExternalCodeUnavailableError
    # error if the import statement failed.

Example of that also checks a version number::

    from bronx.syntax.externalcode import ExternalCodeImportChecker

    echecker = ExternalCodeImportChecker('anypackage')
    with echecker as echecker_register:
        import anypackage
        echecker_register.update(version=anypackage.__version__,
                                 otherthing=anypackage.otherthing)

    # Ensure that the package is here, that version >= 1.0.0 and otherthings==1
    @echecker.disabled_if_unavailable(version='1.0.0', otherthing=1)
    def my_function_based_on_anypackage()
        return anypackage.sayhi()

"""

import re
import sys
import traceback
import types

from bronx.fancies import loggers
from bronx.fancies.display import join_list_in_proper_english

logger = loggers.getLogger(__name__)

if (sys.version_info.minor < 10):
    from distutils.version import LooseVersion as version_cb
else:
    # distutils is now deprecated
    try:
        from packaging.version import parse as version_cb
    except ImportError:

        def version_cb(version1):
            """Crude version processing."""
            return tuple([int(x)
                          for x in re.sub(r'(\.0+)*$', '', version1).split(".")
                          if x.isdigit()])


class ExternalCodeUnavailableError(Exception):
    """Raised by the decorated function/class whenever the import did not succeed."""
    pass


class ExternalCodeImportChecker(object):
    """
    Catches any import error and allow for the developer to test whether it
    succeeded or not.

    See the example above.
    """

    def __init__(self, nickname='external'):
        """
        :param str nickname: The name of the external code to be imported
        """
        self.nickname = nickname
        self._checked_out = None
        self._register = dict()

    def _version_check(self, minimal_version):
        """Check the imported package's version."""
        if 'version' not in self._register:
            raise RuntimeError('No version registered for the {!s} package.'
                               .format(self.nickname))
        return version_cb(self._register['version']) >= version_cb(minimal_version)

    def _item_check(self, itemname, value):
        """Check the imported package's info fits."""
        if itemname not in self._register:
            raise RuntimeError('No {:s} registered for the {!s} package.'
                               .format(itemname, self.nickname))
        return self._register[itemname] == value

    def _kwargs_check(self, kwargs):
        """Check that the kwargs dictionary fits !"""
        accumulate = True
        for k, v in kwargs.items():
            if k in ('version', 'v'):
                accumulate = accumulate and self._version_check(v)
            else:
                accumulate = accumulate and self._item_check(k, v)
        return accumulate

    def __enter__(self):
        return self._register

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Catch any ImportError and deal with it !"""
        if exc_type is None:
            self._checked_out = True
        else:
            if issubclass(exc_type, ImportError):
                logger.warning('The %s package is unavailable.', str(self.nickname))
                logger.info('Associated ' +
                            ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
                self._checked_out = False
                return True

    def is_available(self, **kwargs):
        """Is it ok ?

        :param kwargs: A dictionary of requirements to check for
        """
        if self._checked_out is None:
            raise RuntimeError('No import was attempted yet for package {!s}.'
                               .format(self.nickname))
        return self._checked_out and self._kwargs_check(kwargs)

    def _format_exception_message(self, kwargs):
        """Return  proper error messages."""
        if not kwargs:
            return 'The {!s} package is unavailable.'.format(self.nickname)
        else:
            requirements = [('{!s}>={!s}' if k in ('version', 'v') else '{!s}=={!s}').format(k, v)
                            for k, v in sorted(kwargs.items())]
            return 'The {!s} package is unavailable (with {:s}).'.format(self.nickname,
                                                                         join_list_in_proper_english(requirements))

    def disabled_if_unavailable(self, *kargs, **kwargs):
        """This decorator disables the provided object if the external code is unavailable.

        :param kwargs: A dictionary of requirements to check for
        """
        direct_deco = False
        if kargs:
            if callable(kargs[0]):
                direct_deco = True
            else:
                raise ValueError("kargs needs to be a callable")

        available = self.is_available(** kwargs)

        def actual_disabled_if_unavailable(func_or_cls):
            isfunction = isinstance(func_or_cls, types.FunctionType)
            if not isfunction:
                if not hasattr(func_or_cls, '__new__'):
                    raise TypeError('Old-Style classes are not supported by this module.')
            if available:
                return func_or_cls
            else:
                excmsg = self._format_exception_message(kwargs)
                if isfunction:
                    def error_wrap(*args, **kw):
                        raise ExternalCodeUnavailableError(excmsg)
                    error_wrap.__name__ = func_or_cls.__name__
                    error_wrap.__doc__ = func_or_cls.__doc__
                    return error_wrap
                else:
                    def error_new(*args, **kw):
                        raise ExternalCodeUnavailableError(excmsg)
                    error_new.__name__ = str('__new__')
                    error_new.__doc__ = func_or_cls.__new__.__doc__
                    func_or_cls.__new__ = classmethod(error_new)
                    return func_or_cls

        if direct_deco:
            return actual_disabled_if_unavailable(kargs[0])

        return actual_disabled_if_unavailable
