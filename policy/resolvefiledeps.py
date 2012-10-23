#
# Copyright (c) rPath, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import itertools
import re

from conary.build import policy, use
from conary.deps import deps

class ResolveFileDependencies(policy.PackagePolicy):
    """
    NAME
    ====

    B{C{r.ResolveFileDependencies()}} - Change unresolved C{file:}
    dependencies to trove dependencies

    SYNOPSIS
    ========

    C{r.ResolveFileDependencies([I{exceptions=regexp}])}

    DESCRIPTION
    ===========

    The C{r.ResolveFileDependencies()} policy finds C{file:} requirements
    that are not resolved by C{file:} provides, and replaces them with
    appropriate C{trove:} requirements in the trove.  It does not
    modify the requirements on the individual file objects.

    The C{exceptions} keyword matches file dependencies not to modify.

    The C{r.ResolveFileDependencies()} policy looks up paths first in
    the local database (add items to C{buildRequires} in the recipe to
    ensure that packages are in the local database), and secondarily
    searches the C{installLabelPath}.

    EXAMPLES
    ========

    C{r.ResolveFileDependencies(exceptions='.*')}

    Do not convert any file requirement to a trove requirement.

    C{r.ResolveFileDependencies(exceptions='/usr/sbin/httpd')}

    Do not convert the C{/usr/sbin/http} file requirement to a trove
    requirement.
    """

    requires = (
        ('RemoveSelfProvidedRequires', policy.CONDITIONAL_PRIOR),
        ('Requires', policy.REQUIRED_PRIOR),
    )
    processUnmodified = True

    def do(self):
        self.cfg = self.recipe.cfg
        self.repos = self.recipe.getRepos()
        self.db = self.recipe._db

        if use.Use.bootstrap._get():
            return

        if not hasattr(self.recipe, 'RemoveSelfProvidedRequires'):
            # Compatibility with conary 2.0.50 and earlier
            for comp in self.recipe.autopkg.getComponents():
                comp.requires -= comp.provides

        for comp in self.recipe.autopkg.getComponents():
            req = comp.requires
            prov = comp.provides

            # get the deps that we want to resolve
            proposedFileDeps = set(req.iterDepsByClass(deps.FileDependencies))
            fileDeps = set()
            if self.exceptions:
                reList = [re.compile(x % self.macros)
                           for x in self.exceptions]
                for f in proposedFileDeps:
                    for r in reList:
                        if r.match(str(f)):
                            break
                    else:
                        fileDeps.add(f)
            else:
                fileDeps = proposedFileDeps

            if not fileDeps:
                continue

            addedTroveDeps = []
            removedFileDeps = []

            self.resolveLocal(fileDeps, comp, addedTroveDeps, removedFileDeps)
            self.resolveRepo(fileDeps, comp, addedTroveDeps, removedFileDeps)

            # update the components deps
            if len(addedTroveDeps):
                req.addDeps(deps.TroveDependencies,addedTroveDeps)
                req.removeDeps(deps.FileDependencies,removedFileDeps)

    def resolveLocal(self, fileDeps, comp, addedTroveDeps, removedFileDeps):
        if not fileDeps:
            return

        locDepSets = set()
        trvMap = {}
        for fDep in fileDeps.copy():
            f = str(fDep)
            trv0 = None
            for trv in self.db.iterTrovesByPath(f):
                if not trv0:
                    trv0 = trv
                if trv.provides().satisfies(
                    self.toDepSet(fDep,deps.FileDependencies)):
                    break
            else:
                if trv0:
                    trovName = trv0.getName()
                    self.info("Replacing requirement on file %s with a "
                            "requirement on trove %s since that file is not "
                            "directly provided." % (f, trovName))
                    addedTroveDeps.append(deps.Dependency(trovName))
                    removedFileDeps.append(fDep)
                    fileDeps.remove(fDep)

    def resolveRepo(self,fileDeps, comp, addedTroveDeps, removedFileDeps):
        if not fileDeps:
            return

        resolvedDeps = set()
        for label in self.cfg.installLabelPath:
            solMap = self.repos.resolveDependencies(
                label, self.toDepSets(fileDeps,deps.FileDependencies),
                leavesOnly=True)
            for r in solMap:
                solList = solMap[r]
                for s in itertools.chain(*solList):
                    if s[2].satisfies(comp.flavor):
                        fDep = list(r.iterDeps())[0][1]
                        resolvedDeps.add(fDep)
                        break
        unresolvedDeps = fileDeps - resolvedDeps

        if not unresolvedDeps:
            return

        paths = [str(x) for x in unresolvedDeps]
        trvMap = {}
        presolvedDeps = set()
        for label in self.cfg.installLabelPath:
            pathDict = self.repos.getTroveLeavesByPath(paths, label)
            for p in pathDict:
                if p not in trvMap and pathDict[p]:
                    trvMap[p] = pathDict[p]
                    presolvedDeps.add(deps.Dependency(p))

        if not presolvedDeps:
            return

        for fDep in presolvedDeps:
            f = str(fDep)
            for nvf in trvMap[f]:
                if nvf[2].satisfies(comp.flavor):
                    trovName = nvf[0]
                    self.info("Replacing requirement on file %s with a "
                            "requirement on trove %s since that file is not "
                            "directly provided." % (f, trovName))
                    addedTroveDeps.append(deps.Dependency(trovName))
                    removedFileDeps.append(fDep)
                    fileDeps.remove(fDep)
                    break

    def toDepSet(self, dep, depClass):
        ds = deps.DependencySet()
        ds.addDep(depClass, dep)
        return ds

    def toDepSets(self, deps, depClass):
        s = set()
        for d in deps:
            ds = self.toDepSet(d,depClass)
            s.add(ds)
        return s
