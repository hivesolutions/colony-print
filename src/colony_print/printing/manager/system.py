#!/usr/bin/python
# -*- coding: utf-8 -*-

import parser
import exceptions

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

    def print_test(self, printing_options = {}):
        # retrieves the printing plugin for the given
        # printing options
        printing_plugin = self._get_printing_plugin(printing_options)

        # prints the test in the printing plugin
        printing_plugin.print_test(printing_options)

    def print_test_image(self, printing_options = {}):
        # retrieves the plugin manager
        plugin_manager = self.plugin.manager

        # retrieves the plugin path
        plugin_path = plugin_manager.get_plugin_path_by_id(self.plugin.id)

        # creates the complete image path
        image_path = plugin_path + "/" + TEST_IMAGE_PATH

        # retrieves the printing plugin for the given
        # printing options
        printing_plugin = self._get_printing_plugin(printing_options)

        # prints the test image in the printing plugin
        printing_plugin.print_test_image(image_path, printing_options)

    def print_printing_language(self, printing_language_string, printing_options = {}):
        # creates a new printing language parser
        _parser = parser.PrintingLanguageParser()

        # sets the printing language string in the parser
        _parser.string = printing_language_string

        # parses the string
        _parser.parse_string()

        # retrieves the printing document
        printing_document = _parser.get_value()

        # retrieves the printing plugin for the given
        # printing options
        printing_plugin = self._get_printing_plugin(printing_options)

        # prints the printing language document in the printing plugin
        printing_plugin.print_printing_language(printing_document, printing_options)

    def load_handler(self, handler):
        # retrieves the printing name from the handler and
        # uses it to register the handler in the proper map
        printing_name = handler.get_name()
        self.handlers_map[printing_name] = handler

    def unload_handler(self, printing_plugin):
        # retrieves the printing name from the printing plugin
        printing_name = printing_plugin.get_printing_name()

        # unsets the printing plugin from the printing plugins map
        del self.printing_plugins_map[printing_name]

    def _get_printing_plugin(self, printing_options):
        # retrieves the printing name (engine) from the printing options
        printing_name = printing_options.get("printing_name", None)

        # in case the printing name is defined
        if printing_name:
            # tries to retrieve the printing plugin from the printing plugins
            # map
            printing_plugin = self.printing_plugins_map.get(printing_name, None)
        else:
            if self.plugin.printing_plugins:
                # retrieves the first printing plugin
                printing_plugin = self.plugin.printing_plugins[0]
            else:
                # sets the printing plugin as invalid, because there
                # is not printing plugin available
                printing_plugin = None

        # in case no printing plugin is selected
        if not printing_plugin:
            # raises the printing not available exception
            raise exceptions.PrintingPluginNotAvailable("the required printer is not available or no printers are available")

        # returns the printing plugin
        return printing_plugin
