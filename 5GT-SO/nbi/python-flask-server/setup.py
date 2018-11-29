# coding: utf-8

import sys
from setuptools import setup, find_packages

NAME = "swagger_server"
VERSION = "1.0.0"

# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = ["connexion"]

setup(
    name=NAME,
    version=VERSION,
    description="5GT-SO NBI",
    author_email="",
    url="",
    keywords=["Swagger", "5GT-SO NBI"],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={"": ["swagger/swagger.yaml"]},
    include_package_data=True,
    entry_points={
        "console_scripts": ["swagger_server=swagger_server.__main__:main"]},
    long_description="""\
    REST-API server for the North Bound Interface of the 5GT-SO. Find more at http://5g-transformer.eu
    """
)
