from setuptools import setup, find_packages

setup(
    name='osmclient',
    version_command=('git describe --match v* --tags --long --dirty',
                     'pep440-git'),
    author='Mike Marchetti',
    author_email='mmarchetti@sandvine.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click', 'prettytable', 'pyyaml', 'pycurl', 'python-magic'
    ],
    setup_requires=['setuptools-version-command'],
    test_suite='nose.collector',
    entry_points='''
        [console_scripts]
        osm=osmclient.scripts.osm:cli
        ''',
)
