#!/usr/bin/python
# -*- coding: utf-8 -*-

class PrintingManagerException(Exception):
    """
    The printing manager exception class.
    """

    message = None
    """ The exception's message """

class PrintingPluginNotAvailable(PrintingManagerException):
    """
    The printing plugin not available name class.
    """

    def __init__(self, message):
        """
        Constructor of the class.

        :type message: String
        :param message: The message to be printed.
        """

        PrintingManagerException.__init__(self)
        self.message = message

    def __str__(self):
        """
        Returns the string representation of the class.

        :rtype: String
        :return: The string representation of the class.
        """

        return "Printing plugin not available - %s" % self.message
