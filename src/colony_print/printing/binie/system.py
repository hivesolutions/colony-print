#!/usr/bin/python
# -*- coding: utf-8 -*-

import colony.base.system

import visitor

PRINTING_NAME = "binie"
""" The printing name """

class PrintingBinie(colony.base.system.System):
    """
    The printing binie class.
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
