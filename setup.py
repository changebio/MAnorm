from distutils.core import setup
from distutils.command.install import INSTALL_SCHEMES

for scheme in INSTALL_SCHEMES.values():
    scheme['data'] = scheme['purelib']

VERSION = "1.0.2"
CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
    'Enviroment :: Console',
    'Intended Audience :: Science/Research ',
    'Intended Audience :: Education ',
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'Operating System :: POSIX :: Linux',
    'Operating System :: Unix',
	'Programming Language :: Python::2.7',
    'Topic :: Scientific/Engineering :: Bio-Informatics',
]

install_requires = [
    'numpy',
    'scipy',
    'pandas',
]


setup(
    name="MAnorm",
    description="MAnorm Version,fast but more memory",
    version=VERSION,
    author="Semal",
    author_email="gzhsss2@gmail.com",
    url="www.github.com/semal",
    download_url="xxxxxx",
    package_dir={'MAnorm': 'MAnorm'},
    packages=['MAnorm'],
    scripts=['bin/MAnorm'],
    classifiers=CLASSIFIERS,
)


