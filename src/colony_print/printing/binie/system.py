#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import visitor

PRINTING_NAME = "binie"
""" The printing name """

class PrintingBinie(object):
    """
    The printing binie class, responsible for the handling
    of the front-end of the printing to binie support.
    """

    def get_name(self):
        return PRINTING_NAME

    def print_test(self, options = {}):
        pass

    def print_test_image(self, image_path, options = {}):
        pass

    def print_language(self, printing_document, options = {}):
        # creates the PDF printing visitor then sets the
        # provided printing options in the visitor
        _visitor = visitor.Visitor()
        _visitor.set_options(options)

        # accepts the visitor in the printing document,
        # using double visiting mode
        printing_document.accept_double(_visitor)
