#
# Copyright (c) 2004-2006 rPath, Inc.
#
# This program is distributed under the terms of the Common Public License,
# version 1.0. A copy of this license should have been distributed with this
# source file in a file called LICENSE. If it is not present, the license
# is always available at http://www.opensource.org/licenses/cpl.php.
#
# This program is distributed in the hope that it will be useful, but
# without any waranty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the Common Public License for
# full details.
#

import os
import re
import stat

from conary.lib import util
from conary.build import policy


class BadFilenames(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.BadFilenames()}} - Require absence of newlines in filenames
    information
    
    SYNOPSIS
    ========

    C{r.BadFilenames([I{filterexp}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.BadFilenames()} is typically called
    from within a Conary recipe to require filenames must not contain newlines
    as filenames are separated by newlines in several conary protocols.
    
    No exceptions are allowed.
    
    EXAMPLES
    ========
    
    FIXME NEED EXAMPLE
    """
    def test(self):
        assert(not self.exceptions)
        return True
    def doFile(self, path):
        if path.find('\n') != -1:
            self.error("path %s has illegal newline character", path)


class NonUTF8Filenames(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.NonUTF8Filenames()}} - Require absence of newlines in filenames
    information
    
    SYNOPSIS
    ========

    C{r.NonUTF8Filenames([I{filterexp}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.NonUTF8Filenames()} is typically called
    from within a Conary recipe to require filenames be encoded as UTF-8 as
    that is the standard filename encoding system.
    
    EXAMPLES
    ========
    
    FIXME NEED EXAMPLE
    """
    def doFile(self, path):
        try:
            path.decode('utf-8')
        except UnicodeDecodeError:
            self.error('path "%s" is not valid UTF-8', path)


class NonMultilibComponent(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.NonMultilibComponent()}} - Enforces multilib support
    information
    
    SYNOPSIS
    ========

    C{r.NonMultilibComponent([I{filterexp}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.NonMultilibComponent()} is typically called
    from within a Conary recipe to enforce multilib support so that both
    32-bit, and 64-bit components may be installed for Python, and Perl.
    
    Python and Perl components should generally be under C{/usr/lib}, unless
    they have binaries and are built on a 64-bit platform, in which case
    they should have no files under C{/usr/lib}.
    
    EXAMPLES
    ========
    
    FIXME NEED EXAMPLE
    """
    invariantsubtrees = [
        '%(libdir)s/',
        '%(prefix)s/lib/',
    ]
    invariantinclusions = [
        '.*/python[^/]*/site-packages/.*',
        '.*/perl[^/]*/vendor-perl/.*',
    ]
    invariantexceptions = [
        '%(debuglibdir)s/',
    ]

    def __init__(self, *args, **keywords):
        self.foundlib = {'python': False, 'perl': False}
        self.foundlib64 = {'python': False, 'perl': False}
        self.reported = {'python': False, 'perl': False}
        self.productMapRe = re.compile(
            '.*/(python|perl)[^/]*/(site-packages|vendor-perl)/.*')
	policy.EnforcementPolicy.__init__(self, *args, **keywords)

    def test(self):
	if self.macros.lib == 'lib':
	    # no need to do anything
	    return False
        return True

    def doFile(self, path):
        if not False in self.reported.values():
            return
        # we've already matched effectively the same regex, so should match...
        p = self.productMapRe.match(path).group(1)
        if self.reported[p]:
            return
        if self.currentsubtree == '%(libdir)s/':
            self.foundlib64[p] = path
        else:
            self.foundlib[p] = path
        if self.foundlib64[p] and self.foundlib[p] and not self.reported[p]:
            self.error(
                '%s packages may install in /usr/lib or /usr/lib64,'
                ' but not both: at least %s and %s both exist',
                p, self.foundlib[p], self.foundlib64[p])
            self.reported[p] = True


class NonMultilibDirectories(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.NonMultilibDirectories()}} - Enforces appropriate platform directory
    names
    
    SYNOPSIS
    ========

    C{r.NonMultilibDirectories([I{filterexp}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.NonMultilibDirectories()} is typically called
    from within a Conary recipe to enforce proper directories, relavent to
    platform. 
    
    Troves for 32-bit platforms should not normally contain directories named
    "C{lib64}".
    
    EXAMPLES
    ========
    
    FIXME NEED EXAMPLE
    """
    invariantinclusions = [ ( '.*/lib64', stat.S_IFDIR ), ]

    def test(self):
	if self.macros.lib == 'lib64':
	    # no need to do anything
	    return False
        return True

    def doFile(self, path):
        self.error('path %s has illegal lib64 component on 32-bit platform',
                   path)


class CheckDestDir(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.CheckDestDir()}} - Searches for destination directory in file paths
    and symbolic links contents
    
    SYNOPSIS
    ========

    C{r.CheckDestDir([I{filterexp}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.CheckDestDir()} is typically called
    from within a Conary recipe to search for the C{%(destdir)s} path in file
    paths and symbolic link contents. 
    
    The C{%(destdir)s} should not be contained within file paths and symbolic
    link contents.
    
    Though files should also not contain C{%(destdir)s}, C{r.CheckDestDir}
    does not search inside files.
    
    EXAMPLES
    ========
    
    FIXME NEED EXAMPLE
    """
    def doFile(self, file):
	d = self.macros.destdir
        b = self.macros.builddir

	if file.find(d) != -1:
            self.error('Path %s contains destdir %s', file, d)
	fullpath = d+file
	if os.path.islink(fullpath):
	    contents = os.readlink(fullpath)
	    if contents.find(d) != -1:
                self.error('Symlink %s contains destdir %s in contents %s',
                           file, d, contents)
	    if contents.find(b) != -1:
                self.error('Symlink %s contains builddir %s in contents %s',
                           file, b, contents)

        badRPATHS = (d, b, '/tmp', '/var/tmp')
        m = self.recipe.magic[file]
        if m and m.name == "ELF":
            rpaths = m.contents['RPATH'] or ''
            for rpath in rpaths.split(':'):
                for badRPATH in badRPATHS:
                    if rpath.startswith(badRPATH):
                        self.warn('file %s has illegal RPATH %s',
                                    file, rpath)
                        break


class FilesForDirectories(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.FilesForDirectories()}} - Warn about files where directories are
    expected
    
    SYNOPSIS
    ========

    C{r.FilesForDirectories([I{filterexp}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.FilesForDirectories()} is typically called
    from within a Conary recipe to warn about files where directories are
    expected.
    
    This condition is normally caused by bad C{r.Install()} invocations.
    
    This policy does not honor exceptions.
    
    EXAMPLES
    ========
    
    FIXME NEED EXAMPLE
    """
    # This list represents an attempt to pick the most likely directories
    # to make these mistakes with: directories potentially inhabited by
    # files from multiple packages, with reasonable possibility that they
    # will have files installed by hand rather than by a "make install".
    candidates = (
	'/bin',
	'/sbin',
	'/etc',
	'/etc/X11',
	'/etc/init.d',
	'/etc/sysconfig',
	'/etc/xinetd.d',
	'/lib',
	'/mnt',
	'/opt',
	'/usr',
	'/usr/bin',
	'/usr/sbin',
	'/usr/lib',
	'/usr/libexec',
	'/usr/include',
	'/usr/share',
	'/usr/share/info',
	'/usr/share/man',
	'/usr/share/man/man1',
	'/usr/share/man/man2',
	'/usr/share/man/man3',
	'/usr/share/man/man4',
	'/usr/share/man/man5',
	'/usr/share/man/man6',
	'/usr/share/man/man7',
	'/usr/share/man/man8',
	'/usr/share/man/man9',
	'/usr/share/man/mann',
	'/var/lib',
	'/var/spool',
    )
    def do(self):
	d = self.recipe.macros.destdir
	for path in self.candidates:
	    fullpath = util.joinPaths(d, path)
	    if os.path.exists(fullpath):
		if not os.path.isdir(fullpath):
                    # XXX only report error if directory is included in
                    # the package; if it is merely in the filesystem
                    # only log a warning.  Needs to follow ExcludeDirectories...
                    self.error(
                        'File %s should be a directory; bad r.Install()?', path)


class ObsoletePaths(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.ObsoletePaths()}} - Warn about paths considered obsolete
    
    SYNOPSIS
    ========

    C{r.ObsoletePaths([I{filterexp}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.ObsoletePaths()} is typically called
    from within a Conary recipe to warn about paths which were at one time
    considered correct, but are now considered obsolete.
    
    Note: this policy class does not honor exceptions.
    
    EXAMPLES
    ========
    
    FIXME NEED EXAMPLE
    """

    requires = (
        ('ExcludeDirectories', policy.REQUIRED_PRIOR),
    )

    candidates = {
	'/usr/man': '/usr/share/man',
	'/usr/info': '/usr/share/info',
	'/usr/doc': '/usr/share/doc',
    }
    def do(self):
	d = self.recipe.macros.destdir
	for path in self.candidates.keys():
	    fullpath = util.joinPaths(d, path)
	    if os.path.exists(fullpath):
                # FIXME only report error if directory is included in
                # the package or a file within the directory is included
                # in the package; if it is merely an empty directory in
                # the filesystem only log a warning.
                self.error('Path %s should not exist, use %s instead',
                           path, self.candidates[path])


class PythonEggs(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.PythonEggs()}} - Enforce absence of Python .egg files
    
    SYNOPSIS
    ========

    C{r.PythonEggs([I{filterexp}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.PythonEggs()} is typically called
    from within a Conary recipe to enforce the absence of Python C{.egg}
    files, which are incompatible with package management.
    
    Python  packages should be built with the
    C{--single-version-externally-managed} command line argument, in which
    case the C{.egg} files will not be created.
    
    EXAMPLES
    ========
    
    FIXME NEED EXAMPLE
    """
    invariantinclusions = [
        '.*/python[^/]*/site-packages/.*\.egg',
    ]

    def doFile(self, path):
        self.error('Python .egg %s exists; use'
                   ' --single-version-externally-managed argument'
                   ' to setup.py or use r.PythonSetup()', path)
