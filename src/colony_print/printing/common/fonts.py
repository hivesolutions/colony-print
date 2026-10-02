#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import json
import time
import uuid
import base64
import struct
import hashlib

import appier

FONT_STYLES = ("regular", "bold", "italic", "bold_italic")
""" The sequence of styles of the fonts of a family, the ones
that may be selected by the text elements of the documents """

FONT_FIELDS = ("name", "style", "url", "md5", "data_b64")
""" The sequence of fields of the entries of the fonts of a
print request (and of the font elements of XMPL documents) """

FONT_NAME_SIZE = 31
""" The maximum size of the name of a font, as limited by the
face name of the fonts of windows (GDI) without its terminator """

FONT_MAX_SIZE = 16 * 1024 * 1024
""" The default maximum size (in bytes) of each font file,
larger font files are refused by the font cache """

FONT_SCHEMES = ("http", "https")
""" The schemes of the URLs from which fonts may be downloaded """

FONT_TIMEOUT = 60
""" The timeout (in seconds) of the download of a font file """

TRUE_TYPE_VERSIONS = (b"\x00\x01\x00\x00", b"true")
""" The versions (first bytes) of the true type font files, the
ones with true type outlines (supported by the PDF context) """

MD5_REGEX = re.compile("^[0-9a-fA-F]{32}$")
""" The regular expression that matches the (hexadecimal) MD5
of a font file, the name of its file in the font cache """

INDEX_NAME = "index.json"
""" The name of the file of the index of the font cache """


def verify_font(font, reference=True):
    """
    Verifies that the provided entry of the fonts of a print request
    is valid, with the name of the font and exactly one source for its
    file, the data (base64), the URL or the MD5 of a font already in
    the font cache (as a reference), raising an exception otherwise.

    :type font: Dictionary
    :param font: The font entry to be verified.
    :type reference: bool
    :param reference: If the font may be referenced by its MD5 only,
    without the data or the URL of its file.
    """

    # verifies the structure of the entry and its name, that must fit
    # the face name of the fonts of windows (as the documents use it)
    appier.verify(isinstance(font, dict), message="Font must be an object", code=400)
    name = font.get("name", None)
    appier.verify(
        name and appier.legacy.is_string(name),
        message="Font name must be provided",
        code=400,
    )
    appier.verify(
        len(name) <= FONT_NAME_SIZE,
        message="Font name '%s' is longer than %d characters" % (name, FONT_NAME_SIZE),
        code=400,
    )

    # verifies the style of the font, which is optional as it's read
    # from the font file when it's not provided
    style = font.get("style", None)
    appier.verify(
        style == None or style in FONT_STYLES,
        message="Font style '%s' is not valid" % style,
        code=400,
    )

    # verifies that a single source of the font file is provided, an MD5
    # alone (reference) being a source only when references are allowed
    url = font.get("url", None)
    md5 = font.get("md5", None)
    data_b64 = font.get("data_b64", None)
    sources = "data_b64, url or md5" if reference else "data_b64 or url"
    appier.verify(
        not (data_b64 and url),
        message="Only one of data_b64 or url must be provided for font '%s'" % name,
        code=400,
    )
    appier.verify(
        data_b64 or url or (md5 and reference),
        message="Either %s must be provided for font '%s'" % (sources, name),
        code=400,
    )

    # verifies the format of the URL and of the MD5, note that the MD5 is
    # the name of the font file in the font cache (no other names allowed)
    appier.verify(
        not url
        or (
            appier.legacy.is_string(url)
            and url.split(":", 1)[0].lower() in FONT_SCHEMES
        ),
        message="Font URL '%s' is not valid" % url,
        code=400,
    )
    appier.verify(
        not md5 or (appier.legacy.is_string(md5) and MD5_REGEX.match(md5)),
        message="Font MD5 '%s' is not valid" % md5,
        code=400,
    )
    appier.verify(
        not data_b64 or appier.legacy.is_string(data_b64, all=True),
        message="Font data of '%s' is not valid" % name,
        code=400,
    )


def font_info(data):
    """
    Retrieves the family name and the style of the provided true type
    font file, the family name being the one windows (GDI) uses to
    select the font (name of the windows platform with identifier 1).

    Only (single) true type fonts are supported, as the PDF context is
    only able to embed fonts with true type outlines, meaning that both
    the OpenType fonts with PostScript (CFF) outlines and the font
    collections are refused (an exception is raised).

    :type data: String
    :param data: The contents of the font file.
    :rtype: Tuple
    :return: The family name and the style of the font.
    """

    import reportlab.pdfbase.ttfonts

    # verifies the version of the font file so that the fonts that are
    # not supported are refused with a proper message
    version = data[:4]
    appier.verify(
        not version == b"OTTO",
        message="Fonts with PostScript (CFF) outlines are not supported",
    )
    appier.verify(not version == b"ttcf", message="Font collections are not supported")
    appier.verify(version in TRUE_TYPE_VERSIONS, message="Font is not a TrueType font")

    # parses the font file, an exception is raised in case the file is
    # not valid or in case the font doesn't allow its embedding
    font = reportlab.pdfbase.ttfonts.TTFontFile(appier.legacy.BytesIO(data))

    # iterates over the names of the font to find the family name of the
    # windows platform, preferring the english (united states) one
    name = font.get_table("name")
    _format, count, offset = struct.unpack(">HHH", name[:6])
    family = None
    for index in appier.legacy.xrange(count):
        platform_id, _encoding_id, language_id, name_id, length, start = (
            struct.unpack_from(">HHHHHH", name, 6 + index * 12)
        )
        if not platform_id == 3 or not name_id == 1:
            continue
        if family and not language_id == 0x0409:
            continue
        start += offset
        family = name[start : start + length].decode("utf-16-be")
    appier.verify(family, message="Font has no Windows family name")

    # retrieves the style of the font from its selection flags, that
    # define if the font is italic (first bit) and bold (sixth bit)
    os2 = font.get_table("OS/2")
    selection = struct.unpack(">H", os2[62:64])[0]
    bold, italic = selection & 0x20, selection & 0x01
    if bold and italic:
        style = "bold_italic"
    elif bold:
        style = "bold"
    elif italic:
        style = "italic"
    else:
        style = "regular"

    return family, style


def font_file(font_files, name, style, exact=False):
    """
    Retrieves the path to the file of the font installed on demand with
    the provided name and style, in case the style is not installed for
    the family another style of the family is used (unless the exact
    style is required), as windows (GDI) synthesizes the missing styles
    of a family.

    :type font_files: Dictionary
    :param font_files: The map associating the (lower cased) name and
    the style of the fonts installed on demand with their files.
    :type name: String
    :param name: The name of the font (family) to be retrieved.
    :type style: String
    :param style: The style of the font to be retrieved.
    :type exact: bool
    :param exact: If only the provided style of the family may be used,
    as when the system may have the font of that exact style.
    :rtype: String
    :return: The path to the file of the font or an invalid value
    in case the family (or the exact style) is not installed.
    """

    if not font_files:
        return None
    name_l = name.lower()
    styles = (style,) if exact else (style, "regular") + FONT_STYLES
    for _style in styles:
        file_path = font_files.get((name_l, _style), None)
        if file_path:
            return file_path
    return None


def register_font(font):
    """
    Registers the provided (true type) font in the PDF context, making
    sure that it replaces the font of another file previously registered
    with its name or with its face, as reportlab keeps the first font
    registered for a name or for a face (eg: an older version of a font
    installed on demand or a font of the system with the same name).

    The fonts of the same file share the same registered font, as a
    document can't embed two fonts with the same face.

    :type font: TTFont
    :param font: The (true type) font to be registered.
    """

    import reportlab.pdfbase.pdfmetrics

    # registers the font and verifies that the font registered for its
    # name is the one of its file, returning immediately if that's the case
    reportlab.pdfbase.pdfmetrics.registerFont(font)
    name, face_name, file_path = font.fontName, font.face.name, font.face.filename
    registered = reportlab.pdfbase.pdfmetrics.getFont(name)
    if getattr(registered.face, "filename", None) == file_path:
        return

    # replaces the font registered for the name and for the face, using
    # the font already registered for the face in case it's of the same
    # file (so that the fonts of the same file share the same font)
    face_font = reportlab.pdfbase.pdfmetrics._dynFaceNames.get(face_name, None)
    if face_font and getattr(face_font.face, "filename", None) == file_path:
        font = face_font
    reportlab.pdfbase.pdfmetrics._fonts[name] = font
    reportlab.pdfbase.pdfmetrics._dynFaceNames[face_name] = font


def verify_xmpl(data):
    """
    Verifies that the provided XMPL document may be printed by a node,
    with a printing document as its root element and only with inline
    images (source), as the paths of the images would be read from the
    file system of the node (any file the node is able to read), raising
    an exception otherwise.

    :type data: String
    :param data: The XMPL document to be verified.
    :see: https://github.com/hivesolutions/colony-print/blob/master/doc/xmpl.md
    """

    import xml.dom.minidom

    # verifies the root element of the document, as the parser of the
    # printing language takes any root element as the printing document,
    # and that no element has a path, as the path of an image may come
    # from the image or from any of its ancestors (context)
    document = xml.dom.minidom.parseString(data)
    appier.verify(
        document.documentElement.tagName == "printing_document",
        message="Root element of the document is not a printing document",
        code=400,
    )
    appier.verify(
        not [
            element
            for element in document.getElementsByTagName("*")
            if element.hasAttribute("path")
        ],
        message="Images of the document must be inline (source)",
        code=400,
    )


def xmpl_fonts(data):
    """
    Retrieves the fonts declared by the provided XMPL document, in the
    font elements of its printing document, as entries of the fonts of
    a print request.

    An exception is raised in case the data is not a valid XML document.

    :type data: String
    :param data: The XMPL document to retrieve the fonts.
    :rtype: List
    :return: The entries of the fonts declared by the document.
    :see: https://github.com/hivesolutions/colony-print/blob/master/doc/xmpl.md
    """

    from ..manager import ast
    from ..manager import parser

    # parses the XMPL document retrieving its printing document,
    # the root element of the document
    _parser = parser.PrintingLanguageParser()
    _parser.string = data
    _parser.parse_string()
    document = _parser.get_value()

    # iterates over the elements of the printing document to build
    # the entries of the font elements from their attributes
    fonts = []
    for node in document.child_nodes:
        if not isinstance(node, ast.Font):
            continue
        fonts.append(
            dict(
                (name, getattr(node, name))
                for name in FONT_FIELDS
                if hasattr(node, name)
            )
        )
    return fonts


class FontCache(object):
    """
    The cache of the fonts installed on demand, that keeps the font
    files by their contents (MD5) together with an index associating
    them with the URLs they were downloaded from, so that each font is
    only received or downloaded once.

    The fonts of the cache never expire and the most recently installed
    font of a family and style is the one used (active) for them.
    """

    path = None
    """ The path to the directory where the font files and the
    index of the cache are stored """

    max_size = FONT_MAX_SIZE
    """ The maximum size (in bytes) of each font file """

    fonts = {}
    """ The map associating the MD5 of each font file with its
    information (name, style, size, URL and install time) """

    urls = {}
    """ The map associating the URLs from which the fonts were
    downloaded with the MD5 of their files """

    def __init__(self, path, max_size=FONT_MAX_SIZE):
        """
        Constructor of the class.

        :type path: String
        :param path: The path to the directory of the cache.
        :type max_size: int
        :param max_size: The maximum size (in bytes) of each font file.
        """

        self.path = path
        self.max_size = max_size
        self.fonts = {}
        self.urls = {}

    def load(self):
        """
        Loads the index of the cache from its directory, keeping the
        cache empty in case there's no index (first use).

        An index that is not valid (eg: corrupted by a power loss or
        edited by hand) raises an exception and leaves the cache as it
        is, the font files being kept for their next installation.
        """

        index_path = os.path.join(self.path, INDEX_NAME)
        if not os.path.exists(index_path):
            return
        with open(index_path, "rb") as file:
            index = json.loads(file.read().decode("utf-8"))

        # verifies the information of the fonts of the index (as used to
        # select the active fonts) and the fonts of its URLs, so that an
        # invalid index is refused instead of failing later operations
        fonts = index.get("fonts", {})
        urls = index.get("urls", {})
        for md5, info in fonts.items():
            appier.verify(
                MD5_REGEX.match(md5)
                and appier.legacy.is_string(info["name"])
                and info["style"] in FONT_STYLES
                and isinstance(info["time"], (int, float))
                and isinstance(info.get("order", 0), int),
                message="Font '%s' of the index is not valid" % md5,
            )
        for url, md5 in urls.items():
            appier.verify(
                md5 in fonts,
                message="Font of the URL '%s' of the index is not valid" % url,
            )
        self.fonts = fonts
        self.urls = urls

    def install(self, font):
        """
        Installs the font of the provided entry (of a print request) in
        the cache, receiving it from its data, downloading it from its
        URL (unless the URL is in the cache) or finding it by its MD5, and
        marks it as the font used (active) for its family and style.

        An exception naming the font is raised in case it's not possible
        to install the font or in case it doesn't match its entry.

        :type font: Dictionary
        :param font: The font entry with its name, style and the data
        (base64), the URL or the MD5 of its file.
        :rtype: Dictionary
        :return: The information of the installed font, together with
        its MD5 and the path to its file.
        """

        # verifies the entry and unpacks it into its components, the
        # MD5 being normalized as the hexadecimal digest is lower cased
        verify_font(font)
        name = font["name"]
        style = font.get("style", None)
        url = font.get("url", None)
        md5 = font.get("md5", None)
        md5 = md5.lower() if md5 else md5
        data_b64 = font.get("data_b64", None)

        # retrieves the data of the font file, from the entry itself or
        # downloading it from its URL, unless the font of the URL is
        # already in the cache (URLs are considered immutable)
        data = None
        if data_b64:
            try:
                data = base64.b64decode(data_b64)
            except Exception:
                raise appier.OperationalError(
                    message="Font data of '%s' is not valid" % name, code=400
                )
        elif url and url in self.urls and os.path.exists(self._file(self.urls[url])):
            appier.verify(
                md5 in (None, self.urls[url]),
                message="Font '%s' doesn't match its MD5 '%s'" % (name, md5),
                code=400,
            )
            md5 = self.urls[url]
        elif url:
            data = self._download(name, url)

        # in case there's data for the font verifies its size and its MD5
        # (when provided) and retrieves its information, from the cache or
        # from the font file itself (validating it) when it's not known,
        # otherwise the font must already be in the cache
        if not data == None:
            appier.verify(
                len(data) <= self.max_size,
                message="Font '%s' is larger than %d bytes" % (name, self.max_size),
                code=400,
            )
            md5_data = hashlib.md5(data).hexdigest()
            appier.verify(
                md5 in (None, md5_data),
                message="Font '%s' doesn't match its MD5 '%s'" % (name, md5),
                code=400,
            )
            md5 = md5_data
            info = self.fonts.get(md5, None)
            if not info:
                try:
                    family, family_style = font_info(data)
                except Exception as exception:
                    raise appier.OperationalError(
                        message="Font '%s' is not valid: %s" % (name, exception),
                        code=400,
                    )
                info = dict(name=family, style=family_style, size=len(data))
        else:
            appier.verify(
                md5 in self.fonts and os.path.exists(self._file(md5)),
                message="Font '%s' with MD5 '%s' is not installed" % (name, md5),
                code=400,
            )
            info = self.fonts[md5]

        # verifies that the name and the style of the font are the ones
        # of the entry (the ones used by the documents), before changing
        # the cache so that a font that doesn't match is not installed
        appier.verify(
            name.lower() == info["name"].lower(),
            message="Font '%s' has the family name '%s'" % (name, info["name"]),
            code=400,
        )
        appier.verify(
            style in (None, info["style"]),
            message="Font '%s' has the style '%s' and not '%s'"
            % (name, info["style"], style),
            code=400,
        )

        # stores the font file in the cache (unless it's already there) and
        # marks the font as the most recently installed one (the active one
        # for its family and style) with an order that, unlike the time, is
        # always increasing, saving the index of the cache
        if not data == None and not os.path.exists(self._file(md5)):
            self._write(self._file(md5), data)
        if url:
            info.setdefault("url", url)
            self.urls[url] = md5
        info["time"] = time.time()
        info["order"] = (
            max([0] + [_info.get("order", 0) for _info in self.fonts.values()]) + 1
        )
        self.fonts[md5] = info
        self._save()

        return dict(info, md5=md5, path=self._file(md5))

    def installed(self):
        """
        Retrieves the information of the fonts installed in the cache,
        with a flag that marks the ones used (active) for their family
        and style, sorted by their name, style and install time.

        :rtype: List
        :return: The information of the fonts installed in the cache,
        together with their MD5 and their active flag.
        """

        active = self._active()
        fonts = [
            dict(
                info,
                md5=md5,
                active=active[(info["name"].lower(), info["style"])] == md5,
            )
            for md5, info in self.fonts.items()
        ]
        fonts.sort(key=lambda font: (font["name"].lower(), font["style"], font["time"]))
        return fonts

    def files(self):
        """
        Retrieves the files of the fonts used (active) for each family
        and style, to be used when printing the documents.

        :rtype: Dictionary
        :return: The map associating the (lower cased) name and the style
        of the active fonts with the path to their files.
        """

        return dict((key, self._file(md5)) for key, md5 in self._active().items())

    def _active(self):
        """
        Retrieves the MD5 of the font used (active) for each family and
        style, the most recently installed font of the family and style
        (by its install order and then by its time, for older indexes).

        :rtype: Dictionary
        :return: The map associating the (lower cased) name and the style
        of the fonts with the MD5 of the active font.
        """

        active = {}
        for md5, info in self.fonts.items():
            key = (info["name"].lower(), info["style"])
            current = active.get(key, None)
            current_info = self.fonts[current] if current else None
            if current_info and (
                current_info.get("order", 0),
                current_info["time"],
            ) >= (info.get("order", 0), info["time"]):
                continue
            active[key] = md5
        return active

    def _download(self, name, url):
        """
        Downloads the font file of the provided URL, raising an exception
        naming the font in case it's not possible to download it.

        At most one byte more than the maximum size of the font files is
        read, so that a larger file is refused (by the size verification
        of the font) without being completely loaded in memory.

        :type name: String
        :param name: The name of the font, used for the messages.
        :type url: String
        :param url: The URL of the font file to be downloaded.
        :rtype: String
        :return: The contents of the font file (or its first bytes in
        case it's larger than the maximum size of the font files).
        """

        try:
            response = appier.legacy.urlopen(url, timeout=FONT_TIMEOUT)
            try:
                data = response.read(self.max_size + 1)
            finally:
                response.close()
        except Exception as exception:
            raise appier.OperationalError(
                message="Font '%s' not downloaded from '%s': %s"
                % (name, url, exception),
                code=400,
            )
        return data

    def _file(self, md5):
        """
        Retrieves the path to the file of the font with the provided MD5,
        an invalid MD5 resulting in a path where no font exists.

        :type md5: String
        :param md5: The MD5 of the font file.
        :rtype: String
        :return: The path to the font file in the cache.
        """

        return os.path.join(self.path, "%s.ttf" % md5)

    def _write(self, path, data):
        """
        Writes the provided data into the file of the provided path in
        an atomic fashion, writing a temporary file (flushed to the disk)
        that then replaces the file, so that an interrupted write (even by
        a power loss) never corrupts the file.

        :type path: String
        :param path: The path to the file to be written.
        :type data: String
        :param data: The data to be written in the file.
        """

        if not os.path.exists(self.path):
            os.makedirs(self.path)
        temp_path = "%s.%s.tmp" % (path, str(uuid.uuid4()))
        with open(temp_path, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())

        # replaces the file with the temporary one, note that older
        # versions of python are not able to replace (rename into) an
        # existing file on windows, so the file is removed first there
        # (on the other systems the rename replaces it atomically)
        if hasattr(os, "replace"):
            os.replace(temp_path, path)
        else:
            if os.name == "nt" and os.path.exists(path):
                os.remove(path)
            os.rename(temp_path, path)

    def _save(self):
        """
        Saves the index of the cache (the information of the fonts and
        the URLs they were downloaded from) into its directory.
        """

        index = dict(fonts=self.fonts, urls=self.urls)
        self._write(
            os.path.join(self.path, INDEX_NAME), json.dumps(index).encode("utf-8")
        )
