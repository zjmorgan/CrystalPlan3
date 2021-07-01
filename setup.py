#!/usr/bin/env python
"""Script for installing the CrystalPlan utility."""

# Author: Janik Zikovsky, zikovskyjl@ornl.gov
# Version: $Id$

#--- Imports ---
from setuptools import setup, find_packages

import sys

from crystalplan import CrystalPlan_version

from distutils.extension import Extension

try:
    from Cython.Distutils import build_ext
except ImportError:
    USE_CYTHON = False
else:
    USE_CYTHON = True
    
import numpy as np

if (sys.platform == 'win32'):
    openmp = ''
else:
    openmp = '-fopenmp'

# Two packages: the GUI and the model code
packages = find_packages()
packages = ['crystalplan', \
            'crystalplan.model',  \
            'crystalplan.pyevolve', \
            'crystalplan.gui', \
            'crystalplan.model.pygene']
package_dir = {'crystalplan': 'crystalplan',  
               'crystalplan.pyevolve':'crystalplan/pyevolve', 
               'crystalplan.model':'crystalplan/model', 
               'crystalplan.gui':'crystalplan/gui', 
               'crystalplan.model.pygene':'crystalplan/model/pygene'}

ext = '.pyx' if USE_CYTHON else '.c'

ext_modules = [
    Extension(
        'crystalplan.model.compiled',
        ['crystalplan/model/compiled'+ext],
        extra_compile_args=[openmp],
        extra_link_args=[openmp],
        include_dirs=[np.get_include()]
    )
]

# data_files = [ ('instruments', './instruments/*.csv'),\
#               ('instruments', './instruments/*.xls') ]
data_files = []
package_data = {'crystalplan': ['instruments/*.xls', 'instruments/*.csv', 'instruments/*.detcal',
                                'docs/*.*', 'docs/animations/*.*', 'docs/eq/*.*', 'docs/screenshots/*.*' ],
    'CrystalPlan.model':['data/*.*'],
    'CrystalPlan.gui':['icons/*.png']
}
scripts = ['crystalplan.py']

# Package requirements
install_requires = ['Traits', 'Mayavi', 'numpy', 'scipy']

if (USE_CYTHON):
    cmdclass = {'build_ext': build_ext}
else:
    cmdclass = { }

def pythonVersionCheck():
    # Minimum version of Python
    PYTHON_MAJOR = 3
    PYTHON_MINOR = 6

    if sys.version_info < (PYTHON_MAJOR, PYTHON_MINOR):
        print('You need at least Python %d.%d for %s %s' \
              % (PYTHON_MAJOR, \
                 PYTHON_MINOR, \
                 CrystalPlan_version.package_name, \
                 CrystalPlan_version.version), file=sys.stderr)
        sys.exit(-3)

if __name__ == "__main__":
    pythonVersionCheck()

    setup(
          name=CrystalPlan_version.package_name,
          version=CrystalPlan_version.version,
          description=CrystalPlan_version.description,
          author=CrystalPlan_version.author, 
          author_email=CrystalPlan_version.author_email,
          url=CrystalPlan_version.url,
          scripts=scripts,
          packages=packages,
          package_dir=package_dir,
          data_files=data_files,
          package_data=package_data,
          #include_package_data=True,
          install_requires=install_requires,
          #test_suite='model.test_all.get_all_tests'
          cmdclass=cmdclass,
          ext_modules=ext_modules,
          )
