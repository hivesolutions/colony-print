#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import setuptools

setuptools.setup(
    name = "colony_print",
    version = "0.1.4",
    author = "Hive Solutions Lda.",
    author_email = "development@hive.pt",
    description = "Colony Print Infra-structure",
    license = "Apache License, Version 2.0",
    keywords = "colony print native",
    url = "http://colony_print.hive.pt",
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
        "appier_extras",
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
        "Programming Language :: Python :: 3.6"
    ]
)
