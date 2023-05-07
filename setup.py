#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import setuptools

setuptools.setup(
    name = "colony-print",
    version = "0.2.0",
    author = "Hive Solutions Lda.",
    author_email = "development@hive.pt",
    description = "Colony Print Infra-structure",
    license = "Apache License, Version 2.0",
    keywords = "colony print native",
    url = "http://colony-print.hive.pt",
    zip_safe = False,
    packages = [
        "colony_print",
        "colony_print.controllers",
        "colony_print.printing",
        "colony_print.printing.binie",
        "colony_print.printing.common",
        "colony_print.printing.manager",
        "colony_print.printing.pdf"
    ],
    test_suite = "colony_print.test",
    package_dir = {
        "" : os.path.normpath("src")
    },
    package_data = {
        "colony_print" : [
            "static/example/*",
            "static/example/js/*",
            "static/example/xml/*"
        ]
    },
    install_requires = [
        "appier",
        "appier-extras",
        "jinja2",
        "pillow",
        "reportlab"
    ],
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Topic :: Utilities",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.0",
        "Programming Language :: Python :: 3.1",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7"
    ],
    long_description = open(os.path.join(os.path.dirname(__file__), "README.md"), "rb").read().decode("utf-8"),
    long_description_content_type = "text/markdown"
)
