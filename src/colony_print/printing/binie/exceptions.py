#!/usr/bin/python
# -*- coding: utf-8 -*-

class PrintingBinieException(Exception):
    """
    The printing binie exception class.
    """

    message = None
    """ The exception's message """

class InvalidContextInformationName(PrintingBinieException):
    """
    The invalid context information name class.
    """

    def __init__(self, message):
        """
        Constructor of the class.

        :type message: String
        :param message: The message to be printed.
        """

        PrintingBinieException.__init__(self)
        self.message = message

    def __str__(self):
        """
        Returns the string representation of the class.

        :rtype: String
        :return: The string representation of the class.
        """

        return "Invalid context information name - %s" % self.message
