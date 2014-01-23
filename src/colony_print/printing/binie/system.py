#!/usr/bin/python
# -*- coding: utf-8 -*-

import visitor

PRINTING_NAME = "binie"
""" The printing name """

class PrintingBinie(object):
    """
    The printing binie class, responsible for the handling
    of the front-end of the printing to binie support.
    """

    def get_printing_name(self):
        return PRINTING_NAME

    def print_test(self, printing_options = {}):
        pass

    def print_test_image(self, image_path, printing_options = {}):
        pass

    def print_printing_language(self, printing_document, printing_options = {}):
        # creates the pdf printing visitor then sets the
        # provided printing options in the visitor
        _visitor = visitor.Visitor()
        _visitor.set_printing_options(printing_options)

        # accepts the visitor in the printing document,
        # using double visiting mode
        printing_document.accept_double(_visitor)
