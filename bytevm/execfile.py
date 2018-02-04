"""Execute files of Python code."""

import imp
import os
import sys
import tokenize
import argparse
import logging

from .pyvm2 import VirtualMachine

NoSource = Exception

class ExecFile:

    def exec_code_object(self, code, env):
        vm = VirtualMachine()
        vm.run_code(code, f_globals=env)

    def run_python_module(self, modulename, args):
        """Run a python module, as though with ``python -m name args...``.

        `modulename` is the name of the module, possibly a dot-separated name.
        `args` is the argument array to present as sys.argv, including the first
        element naming the module being executed.

        """
        openfile = None
        glo, loc = globals(), locals()
        try:
            try:
                # Search for the module - inside its parent package, if any - using
                # standard import mechanics.
                if '.' in modulename:
                    packagename, name = modulename.rsplit('.')
                    package = __import__(packagename, glo, loc, ['__path__'])
                    searchpath = package.__path__
                else:
                    packagename, name = None, modulename
                    searchpath = None  # "top-level search" in imp.find_module()
                openfile, pathname, _ = imp.find_module(name, searchpath)

                # Complain if this is a magic non-file module.
                if openfile is None and pathname is None:
                    raise NoSource("module does not live in a file: %r" % modulename)

                # If `modulename` is actually a package, not a mere module, then we
                # pretend to be Python 2.7 and try running its __main__.py script.
                if openfile is None:
                    packagename = modulename
                    name = '__main__'
                    package = __import__(packagename, glo, loc, ['__path__'])
                    searchpath = package.__path__
                    openfile, pathname, _ = imp.find_module(name, searchpath)
            except ImportError:
                _, err, _ = sys.exc_info()
                raise NoSource(str(err))
        finally:
            if openfile:
                openfile.close()

        # Finally, hand the file off to run_python_file for execution.
        args[0] = pathname
        self.run_python_file(pathname, args, package=packagename)


    def run_python_file(self, filename, args, package=None):
        """Run a python file as if it were the main program on the command line.

        `filename` is the path to the file to execute, it need not be a .py file.
        `args` is the argument array to present as sys.argv, including the first
        element naming the file being executed.  `package` is the name of the
        enclosing package, if any.

        """
        # Create a module to serve as __main__
        old_main_mod = sys.modules['__main__']
        main_mod = imp.new_module('__main__')
        sys.modules['__main__'] = main_mod
        main_mod.__file__ = filename
        if package:
            main_mod.__package__ = package
        main_mod.__builtins__ = sys.modules['builtins']

        # Set sys.argv and the first path element properly.
        old_argv = sys.argv
        old_path0 = sys.path[0]
        sys.argv = args
        if package:
            sys.path[0] = ''
        else:
            sys.path[0] = os.path.abspath(os.path.dirname(filename))

        try:
            # Open the source file.
            try:
                source_file = open(filename, 'rU')
            except IOError:
                raise NoSource("No file to run: %r" % filename)

            try:
                source = source_file.read()
            finally:
                source_file.close()

            # We have the source.  `compile` still needs the last line to be clean,
            # so make sure it is, then compile a code object from it.
            if not source or source[-1] != '\n':
                source += '\n'
            code = compile(source, filename, "exec")

            # Execute the source file.
            self.exec_code_object(code, main_mod.__dict__)
        finally:
            # Restore the old __main__
            sys.modules['__main__'] = old_main_mod

            # Restore the old argv and path
            sys.argv = old_argv
            sys.path[0] = old_path0


    def cmdline(self, argv):
        parser = argparse.ArgumentParser(
            prog="bytevm",
            description="Run Python programs with a Python bytecode interpreter.",
        )
        parser.add_argument(
            '-m', dest='module', action='store_true',
            help="prog is a module name, not a file name.",
        )
        parser.add_argument(
            '-v', '--verbose', dest='verbose', action='store_true',
            help="trace the execution of the bytecode.",
        )
        parser.add_argument(
            'prog',
            help="The program to run.",
        )
        parser.add_argument(
            'args', nargs=argparse.REMAINDER,
            help="Arguments to pass to the program.",
        )
        args = parser.parse_args()

        level = logging.DEBUG if args.verbose else logging.WARNING
        logging.basicConfig(level=level)

        new_argv = [args.prog] + args.args
        if args.module:
            self.run_python_module(args.prog, new_argv)
        else:
            self.run_python_file(args.prog, new_argv)

