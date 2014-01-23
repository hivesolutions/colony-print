#!/usr/bin/python
# -*- coding: utf-8 -*-

import visitor

PRINTING_NAME = "pdf"
""" The printing name, for the current pdf
infra-structure (as defined in spec) """

class PrintingPdf(object):
    """
    The printing pdf class, that is responsible for
    the handling of the logic for the printing of pdf
    files based on the xml template language.
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
