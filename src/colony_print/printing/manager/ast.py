#!/usr/bin/python
# -*- coding: utf-8 -*-

class AstNode(object):
    """
    The AST node class, that represents a generic node
    to be percolated as part of the AST (abstract syntax tree).
    """

    value = None
    """ The value """

    indent = False
    """ The indentation level """

    child_nodes = []
    """ The list of child nodes """

    def __init__(self):
        self.child_nodes = []

    def __repr__(self):
        return "<ast_node indent:%s child_nodes:%s>" % (self.indent, len(self.child_nodes))

    def accept(self, visitor):
        visitor.visit(self)

        if visitor.visit_childs:
            for child_node in self.child_nodes:
                child_node.accept(visitor)

    def accept_post_order(self, visitor):
        if visitor.visit_childs:
            for child_node in self.child_nodes:
                child_node.accept_post_order(visitor)

        visitor.visit(self)

    def accept_double(self, visitor):
        visitor.visit_index = 0
        visitor.visit(self)

        if visitor.visit_childs:
            for child_node in self.child_nodes:
                child_node.accept_double(visitor)

        visitor.visit_index = 1
        visitor.visit(self)

    def set_value(self, value):
        self.value = value

    def set_indent(self, indent):
        self.indent = indent

    def add_child_node(self, child_node):
        self.child_nodes.append(child_node)

    def remove_child_node(self, child_node):
        self.child_nodes.remove(child_node)

class GenericElement(AstNode):

    element_name = "none"

    def __init__(self, element_name = "none"):
        AstNode.__init__(self)
        self.element_name = element_name

class PrintingDocument(AstNode):

    def __init__(self):
        AstNode.__init__(self)

class Block(AstNode):

    def __init__(self):
        AstNode.__init__(self)

class Paragraph(AstNode):

    def __init__(self):
        AstNode.__init__(self)

class Line(AstNode):

    def __init__(self):
        AstNode.__init__(self)

class Text(AstNode):

    def __init__(self):
        AstNode.__init__(self)

class Image(AstNode):

    def __init__(self):
        AstNode.__init__(self)
