#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import base
from . import fonts

from .base import visited, dispatch_visit
from .fonts import (
    FONT_STYLES,
    FONT_MAX_SIZE,
    verify_font,
    font_info,
    font_file,
    register_font,
    verify_xmpl,
    xmpl_fonts,
    strip_xmpl_fonts,
    FontCache,
)
