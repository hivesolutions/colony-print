#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import ast

from ..common.base import *

class Visitor(object):
    """
    The visitor class.
    """

    node_method_map = {}
    """ The node method map """

    visit_childs = True
    """ The visit childs flag """

    visit_next = True
    """ The visit next flag """

    visit_index = 0
    """ The visit index, for multiple visits """

    def __init__(self):
        self.node_method_map = {}
        self.visit_childs = True
        self.visit_next = True
        self.visit_index = 0

        self.update_node_method_map()

    def update_node_method_map(self):
        # retrieves the class of the current instance
        self_class = self.__class__

        # retrieves the names of the elements for the current class
        self_class_elements = dir(self_class)

        # iterates over all the name of the elements
        for self_class_element in self_class_elements:
            # retrieves the real element value
            self_class_real_element = getattr(self_class, self_class_element)

            # in case the current class real element does not contain
            # an AST node class reference must continue the loop
            if not hasattr(self_class_real_element, "ast_node_class"): continue

            # retrieves the AST node class from the current class real element
            # and sets it in the node method map
            ast_node_class = getattr(self_class_real_element, "ast_node_class")
            self.node_method_map[ast_node_class] = self_class_real_element

    @dispatch_visit()
    def visit(self, node):
        print("unrecognized element node of type " + node.__class__.__name__)

    def before_visit(self, node):
        self.visit_childs = True
        self.visit_next = True

    def after_visit(self, node):
        pass

    @visited(ast.AstNode)
    def visit_ast_node(self, node):
        print("AstNode: " + str(node))

    @visited(ast.GenericElement)
    def visit_generic_element(self, node):
        print("GenericElement: " + str(node))

    @visited(ast.PrintingDocument)
    def visit_printing_document(self, node):
        print("PrintingDocument: " + str(node))

    @visited(ast.Block)
    def visit_block(self, node):
        print("Block: " + str(node))

    @visited(ast.Paragraph)
    def visit_paragraph(self, node):
        print("Paragraph: " + str(node))

    @visited(ast.Line)
    def visit_line(self, node):
        print("Line: " + str(node))

    @visited(ast.Text)
    def visit_text(self, node):
        print("Text: " + str(node))

    @visited(ast.Image)
    def visit_image(self, node):
        print("Image: " + str(node))
