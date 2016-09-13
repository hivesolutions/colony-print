#!/usr/bin/python
# -*- coding: utf-8 -*-

import os

import appier

from . import parser
from . import exceptions

TEST_IMAGE_PATH = "resources/test_logo.png"
""" The test image relative path to the current
file path (considered the base path) """

class PrintingManager(object):
    """
    The printing manager class, that is responsible for the
    top level handling of the printing operations.
    """

    handlers_map = {}
    """ The map containing an association between the
    name of the printing handler and the proper instance
    that may be used for printing processing """

    def __init__(self):
        self.handlers_map = {}

    def load(self):
        import colony_print
        pdf_handler = colony_print.PrintingPDF()
        binie_handler = colony_print.PrintingBinie()
        self.load_handler(pdf_handler)
        self.load_handler(binie_handler)

    def unload(self):
        for _name, handler in appier.legacy.items(self.handlers_map):
            self.unload_handler(handler)

    def print_test(self, options = {}):
        # retrieves the proper handler using the provided map of options
        # and then uses the same options to run a test print operation
        handler = self._get_handler(options)
        handler.print_test(options)

    def print_test_image(self, options = {}):
        # retrieves the complete path for the current file and then
        # retrieves it's directory path, to be used in the calculus
        # of the image path to be used
        file_path = os.path.realpath(__file__)
        base_path = os.path.dirname(file_path)

        # creates the complete image path using the calculated base
        # path from the current file's path and then appends the relative
        # path to the image resource
        image_path = os.path.join(base_path, TEST_IMAGE_PATH)

        # retrieves the proper printing handler for the provided options
        # and then uses it to print the test image in the calculated path
        handler = self._get_handler(options)
        handler.print_test_image(image_path, options)

    def print_language(self, data, options = {}):
        # creates a new printing language parser and sets the
        # proper data in it running then the parse string operation
        # that is going to be parsing the provided string
        _parser = parser.PrintingLanguageParser()
        _parser.string = data
        _parser.parse_string()

        # retrieves the (printing) document resulting from
        # the parsing of the provided value this value is
        # going to be sent to the handler for "printing"
        document = _parser.get_value()

        # retrieves the proper handler according to the provided
        # options and uses it in the printing operation
        handler = self._get_handler(options)
        handler.print_language(document, options)

    def load_handler(self, handler):
        # retrieves the printing name from the handler and
        # uses it to register the handler in the proper map
        printing_name = handler.get_name()
        self.handlers_map[printing_name] = handler

    def unload_handler(self, handler):
        # gathers the name of the provided handler and then
        # removes any reference to it in the map of handlers
        printing_name = handler.get_name()
        del self.handlers_map[printing_name]

    def _get_handler(self, options):
        # retrieves the printing name (engine) from the printing options
        # this value is going to be used to select the proper handler
        printing_name = options.get("name", None)
        if not printing_name: raise exceptions.PrintingPluginNotAvailable("missing name")

        # tries to retrieve the proper handler for the requested name that
        # exists in the handlers map in case it's not available raises an
        # exception indicating the problem
        handler = self.handlers_map.get(printing_name, None)
        if not handler:
            raise exceptions.PrintingPluginNotAvailable("no handler for requested name")

        # returns the (printing) handler that has been requested according
        # to the provided map of options
        return handler
