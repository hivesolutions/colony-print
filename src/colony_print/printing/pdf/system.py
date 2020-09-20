#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import visitor

PRINTING_NAME = "pdf"
""" The printing name, for the current PDF
infra-structure (as defined in spec) """

class PrintingPDF(object):
    """
    The printing PDF class, that is responsible for
    the handling of the logic for the printing of PDF
    files based on the XML template language.
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
