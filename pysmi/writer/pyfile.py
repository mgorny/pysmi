#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2020, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
import os
import py_compile
import sys
import tempfile

try:
    import importlib

    try:
        SOURCE_SUFFIXES = importlib.machinery.SOURCE_SUFFIXES

    except Exception:
        raise ImportError()

except ImportError:
    import imp

    SOURCE_SUFFIXES = [s[0] for s in imp.get_suffixes() if s[2] == imp.PY_SOURCE]

from pysmi import debug, error
from pysmi.compat import decode, encode
from pysmi.writer.base import AbstractWriter


class PyFileWriter(AbstractWriter):
    """Stores transformed MIB modules as Python files at specified location.

    User is expected to pass *PyFileWriter* class instance to
    *MibCompiler* on instantiation. The rest is internal to *MibCompiler*.
    """

    pyCompile = True
    pyOptimizationLevel = -1

    def __init__(self, path):
        """Creates an instance of *PyFileWriter* class.

        Args:
            path: writable directory to store Python modules
        """
        self._path = decode(os.path.normpath(path))

    def __str__(self):
        return f'{self.__class__.__name__}{{"{self._path}"}}'

    def putData(self, mibname, data, comments=(), dryRun=False):
        if dryRun:
            debug.logger & debug.flagWriter and debug.logger("dry run mode")
            return

        if not os.path.exists(self._path):
            try:
                os.makedirs(self._path)

            except OSError:
                raise error.PySmiWriterError(
                    f"failure creating destination directory {self._path}: {sys.exc_info()[1]}",
                    writer=self,
                )

        if comments:
            data = "#\n" + "".join(["# %s\n" % x for x in comments]) + "#\n" + data

        pyfile = os.path.join(self._path, decode(mibname))
        pyfile += SOURCE_SUFFIXES[0]

        tfile = None

        try:
            fd, tfile = tempfile.mkstemp(dir=self._path)
            os.write(fd, encode(data))
            os.close(fd)
            os.rename(tfile, pyfile)

        except (OSError, UnicodeEncodeError):
            exc = sys.exc_info()
            if tfile and os.access(tfile, os.F_OK):
                os.unlink(tfile)

            raise error.PySmiWriterError(
                f"failure writing file {pyfile}: {exc[1]}", file=pyfile, writer=self
            )

        debug.logger & debug.flagWriter and debug.logger("created file %s" % pyfile)

        if self.pyCompile:
            try:
                py_compile.compile(
                    pyfile, doraise=True, optimize=self.pyOptimizationLevel
                )

            except (SyntaxError, py_compile.PyCompileError):
                pass  # XXX

            except Exception:
                if pyfile and os.access(pyfile, os.F_OK):
                    os.unlink(pyfile)

                raise error.PySmiWriterError(
                    f"failure compiling {pyfile}: {sys.exc_info()[1]}",
                    file=mibname,
                    writer=self,
                )

        debug.logger & debug.flagWriter and debug.logger("%s stored" % mibname)

    def getData(self, filename):
        return ""
