#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import json
import time
import base64
import shutil
import struct
import hashlib
import tempfile
import unittest

import appier

import colony_print

FONTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "assets", "fonts"
)
""" The path to the directory that contains the fonts bundled
with the repository, used by the documents of the tests """

FONT_FILES = dict(
    regular="calibri", bold="calibrib", italic="calibrii", bold_italic="calibriz"
)
""" The map associating the styles of the Calibri font with the
(base) names of the files of the font bundled with the repository """

EXAMPLE = '<?xml version="1.0" encoding="UTF-8"?>\
    <printing_document name="hello_world" font="Colonia" font_size="9">\
        <font name="Colonia" url="https://fonts.hive.pt/colonia.ttf"/>\
        <font name="Colonia" style="bold" md5="%s" data_b64="QUJD"/>\
        <paragraph text_align="center">\
            <font name="Ignored" url="https://fonts.hive.pt/ignored.ttf"/>\
            <line><text>Hello World</text></line>\
        </paragraph>\
    </printing_document>' % ("0" * 32)
""" Example XML string that declares fonts in the font elements
of the printing document (and in a paragraph, where they are
not valid) using the XML printing language """


def build_font(name="Colonia", style="regular"):
    """
    Builds a true type font file from the Calibri font bundled with the
    repository (of the provided style), renaming its family into the
    provided name, so that the font is not installed in the system.

    :type name: String
    :param name: The name of the family of the font, with the same
    size of the original name (Calibri), as the names are replaced.
    :type style: String
    :param style: The style of the font to be built.
    :rtype: String
    :return: The contents of the built font file.
    """

    with open(os.path.join(FONTS_PATH, FONT_FILES[style] + ".ttf"), "rb") as file:
        data = file.read()
    data = data.replace(b"Calibri", name.encode("utf-8"))
    return data.replace("Calibri".encode("utf-16-be"), name.encode("utf-16-be"))


def name_record(data, index, language_id=None, name_id=None):
    """
    Changes the language and/or the name identifier of the record (of
    the provided index) of the names of the provided font file.

    :type data: String
    :param data: The contents of the font file to be changed.
    :type index: int
    :param index: The index of the record of the names to be changed.
    :type language_id: int
    :param language_id: The new language of the record, if any.
    :type name_id: int
    :param name_id: The new name identifier of the record, if any.
    :rtype: String
    :return: The contents of the changed font file.
    """

    count = struct.unpack(">H", data[4:6])[0]
    for table in range(count):
        tag, _checksum, offset, _length = struct.unpack(
            ">4sIII", data[12 + table * 16 : 28 + table * 16]
        )
        if tag == b"name":
            break
    record = offset + 6 + index * 12
    platform_id, encoding_id, _language_id, _name_id, length, start = struct.unpack(
        ">HHHHHH", data[record : record + 12]
    )
    value = struct.pack(
        ">HHHHHH",
        platform_id,
        encoding_id,
        _language_id if language_id == None else language_id,
        _name_id if name_id == None else name_id,
        length,
        start,
    )
    return data[:record] + value + data[record + 12 :]


class FontsTest(unittest.TestCase):
    def test_verify_font(self):
        colony_print.verify_font(dict(name="Colonia", data_b64="QUJD"))
        colony_print.verify_font(
            dict(name="Colonia", style="bold", url="https://fonts.hive.pt/a.ttf")
        )
        colony_print.verify_font(dict(name="Colonia", url="HTTP://fonts.hive.pt/a.ttf"))
        colony_print.verify_font(dict(name="Colonia", md5="A" * 32))
        colony_print.verify_font(
            dict(name="Colonia", md5="a" * 32, data_b64="QUJD"), reference=False
        )
        colony_print.verify_font(dict(name="C" * 31, data_b64="QUJD"))
        for style in colony_print.FONT_STYLES:
            colony_print.verify_font(dict(name="Colonia", style=style, data_b64="QUJD"))

    def test_verify_font_invalid(self):
        invalid = [
            "Colonia",
            ["Colonia"],
            dict(data_b64="QUJD"),
            dict(name="", data_b64="QUJD"),
            dict(name=1, data_b64="QUJD"),
            dict(name="C" * 32, data_b64="QUJD"),
            dict(name="Colonia", style="black", data_b64="QUJD"),
            dict(name="Colonia", style="Bold", data_b64="QUJD"),
            dict(name="Colonia"),
            dict(name="Colonia", style="bold"),
            dict(name="Colonia", data_b64="QUJD", url="https://fonts.hive.pt/a.ttf"),
            dict(name="Colonia", url="ftp://fonts.hive.pt/a.ttf"),
            dict(name="Colonia", url="file:///etc/fonts/a.ttf"),
            dict(name="Colonia", url="fonts.hive.pt/a.ttf"),
            dict(name="Colonia", url=["https://fonts.hive.pt/a.ttf"]),
            dict(name="Colonia", md5="../../../../etc/passwd"),
            dict(name="Colonia", md5="a" * 31),
            dict(name="Colonia", md5="a" * 33),
            dict(name="Colonia", md5="g" * 32),
            dict(name="Colonia", md5=1, data_b64="QUJD"),
        ]
        for font in invalid:
            self.assertRaises(
                appier.OperationalError, lambda: colony_print.verify_font(font)
            )

        self.assertRaises(
            appier.OperationalError,
            lambda: colony_print.verify_font(
                dict(name="Colonia", md5="a" * 32), reference=False
            ),
        )

    def test_font_info(self):
        self.assertEqual(colony_print.font_info(build_font()), ("Colonia", "regular"))
        self.assertEqual(
            colony_print.font_info(build_font(name="Binaria")), ("Binaria", "regular")
        )
        self.assertEqual(
            colony_print.font_info(build_font(style="bold")), ("Colonia", "bold")
        )
        self.assertEqual(
            colony_print.font_info(build_font(style="italic")), ("Colonia", "italic")
        )
        self.assertEqual(
            colony_print.font_info(build_font(style="bold_italic")),
            ("Colonia", "bold_italic"),
        )

    def test_font_info_names(self):
        # the non english family name (the copyright record) comes before
        # the english one, that is the one used
        data = name_record(build_font(), 30, language_id=0x0816, name_id=1)
        self.assertEqual(colony_print.font_info(data), ("Colonia", "regular"))

        # the non english family name (the subfamily record) comes after
        # the english one, that is the one used
        data = name_record(build_font(), 32, language_id=0x0816, name_id=1)
        self.assertEqual(colony_print.font_info(data), ("Colonia", "regular"))

        # the only family name of the windows platform is not english
        data = name_record(build_font(), 31, language_id=0x0816)
        self.assertEqual(colony_print.font_info(data), ("Colonia", "regular"))

        # there's no family name of the windows platform (only the ones
        # of the other platforms), that is the one windows uses
        data = name_record(build_font(), 31, name_id=2)
        self.assertRaises(appier.OperationalError, lambda: colony_print.font_info(data))

    def test_font_info_invalid(self):
        data = build_font()
        self.assertRaises(
            appier.OperationalError, lambda: colony_print.font_info(b"OTTO" + data[4:])
        )
        self.assertRaises(
            appier.OperationalError, lambda: colony_print.font_info(b"ttcf" + data[4:])
        )
        self.assertRaises(
            appier.OperationalError, lambda: colony_print.font_info(b"wOFF" + data[4:])
        )
        self.assertRaises(
            appier.OperationalError, lambda: colony_print.font_info(b"not a font")
        )
        self.assertRaises(appier.OperationalError, lambda: colony_print.font_info(b""))
        self.assertRaises(
            Exception, lambda: colony_print.font_info(b"\x00\x01\x00\x00" + b"\0" * 8)
        )
        self.assertRaises(Exception, lambda: colony_print.font_info(data[:1024]))

    def test_font_file(self):
        font_files = {
            ("colonia", "regular"): "/fonts/colonia.ttf",
            ("colonia", "bold"): "/fonts/coloniab.ttf",
            ("binaria", "italic"): "/fonts/binariai.ttf",
            ("binaria", "bold_italic"): "/fonts/binariaz.ttf",
        }
        font_file = colony_print.font_file
        self.assertEqual(
            font_file(font_files, "Colonia", "regular"), "/fonts/colonia.ttf"
        )
        self.assertEqual(
            font_file(font_files, "COLONIA", "bold"), "/fonts/coloniab.ttf"
        )
        self.assertEqual(
            font_file(font_files, "colonia", "italic"), "/fonts/colonia.ttf"
        )
        self.assertEqual(
            font_file(font_files, "Colonia", "bold_italic"), "/fonts/colonia.ttf"
        )
        self.assertEqual(
            font_file(font_files, "Binaria", "italic"), "/fonts/binariai.ttf"
        )
        self.assertEqual(
            font_file(font_files, "Binaria", "regular"), "/fonts/binariai.ttf"
        )
        self.assertEqual(
            font_file(font_files, "Binaria", "bold"), "/fonts/binariai.ttf"
        )
        self.assertEqual(font_file(font_files, "Calibri", "regular"), None)
        self.assertEqual(font_file(dict(), "Colonia", "regular"), None)
        self.assertEqual(font_file(None, "Colonia", "regular"), None)

    def test_xmpl_fonts(self):
        fonts = colony_print.xmpl_fonts(EXAMPLE)
        self.assertEqual(
            fonts,
            [
                dict(name="Colonia", url="https://fonts.hive.pt/colonia.ttf"),
                dict(name="Colonia", style="bold", md5="0" * 32, data_b64="QUJD"),
            ],
        )
        self.assertEqual(
            colony_print.xmpl_fonts(appier.legacy.bytes(EXAMPLE, encoding="utf-8")),
            fonts,
        )

        self.assertEqual(
            colony_print.xmpl_fonts(
                '<printing_document name="hello_world"><paragraph/></printing_document>'
            ),
            [],
        )

    def test_xmpl_fonts_invalid(self):
        self.assertRaises(
            Exception, lambda: colony_print.xmpl_fonts("<printing_document>")
        )
        self.assertRaises(Exception, lambda: colony_print.xmpl_fonts("not xml"))
        self.assertRaises(Exception, lambda: colony_print.xmpl_fonts(""))


class FontCacheTest(unittest.TestCase):
    def setUp(self):
        self.target_dir = tempfile.mkdtemp(prefix="colony-print-fonts-cache-test-")
        self.path = os.path.join(self.target_dir, "fonts")
        self.downloads = []
        self.responses = dict()
        self._get = appier.get
        appier.get = self._download

    def tearDown(self):
        appier.get = self._get
        shutil.rmtree(self.target_dir, ignore_errors=True)

    def _download(self, url, timeout=None):
        self.downloads.append((url, timeout))
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return response

    def _files(self):
        return sorted(os.listdir(self.path)) if os.path.exists(self.path) else []

    def test_init(self):
        font_cache = colony_print.FontCache(self.path)
        self.assertEqual(font_cache.path, self.path)
        self.assertEqual(font_cache.max_size, colony_print.FONT_MAX_SIZE)
        self.assertEqual(font_cache.fonts, {})
        self.assertEqual(font_cache.urls, {})

        font_cache = colony_print.FontCache(self.path, max_size=1024)
        self.assertEqual(font_cache.max_size, 1024)

    def test_load(self):
        font_cache = colony_print.FontCache(self.path)
        font_cache.load()
        self.assertEqual(font_cache.fonts, {})
        self.assertEqual(font_cache.urls, {})
        self.assertEqual(self._files(), [])

        self.responses["https://fonts.hive.pt/colonia.ttf"] = build_font()
        font_cache.install(
            dict(name="Colonia", url="https://fonts.hive.pt/colonia.ttf")
        )
        font_cache.install(
            dict(name="Colonia", data_b64=base64.b64encode(build_font(style="bold")))
        )

        # loads the index in a new cache (as when the node is restarted)
        # where the fonts may be referenced by their MD5 (no downloads)
        loaded = colony_print.FontCache(self.path)
        loaded.load()
        self.assertEqual(loaded.fonts, font_cache.fonts)
        self.assertEqual(loaded.urls, font_cache.urls)
        self.assertEqual(loaded.installed(), font_cache.installed())
        self.assertEqual(loaded.files(), font_cache.files())

        md5 = hashlib.md5(build_font(style="bold")).hexdigest()
        info = loaded.install(dict(name="Colonia", md5=md5))
        self.assertEqual(info["style"], "bold")
        loaded.install(dict(name="Colonia", url="https://fonts.hive.pt/colonia.ttf"))
        self.assertEqual(len(self.downloads), 1)

    def test_install(self):
        data = build_font()
        md5 = hashlib.md5(data).hexdigest()
        font_cache = colony_print.FontCache(self.path)
        info = font_cache.install(dict(name="Colonia", data_b64=base64.b64encode(data)))
        self.assertEqual(
            info,
            dict(
                name="Colonia",
                style="regular",
                size=len(data),
                time=info["time"],
                md5=md5,
                path=os.path.join(self.path, md5 + ".ttf"),
            ),
        )
        self.assertEqual(self._files(), [md5 + ".ttf", "index.json"])
        with open(info["path"], "rb") as file:
            self.assertEqual(file.read(), data)
        with open(os.path.join(self.path, "index.json"), "rb") as file:
            index = json.loads(file.read().decode("utf-8"))
        self.assertEqual(index, dict(fonts=font_cache.fonts, urls=dict()))

        # installs the same font again (with another name case, the given
        # style and MD5) which only marks it as the most recent one
        time.sleep(0.01)
        installed = font_cache.install(
            dict(
                name="COLONIA",
                style="regular",
                md5=md5.upper(),
                data_b64=base64.b64encode(data).decode("utf-8"),
            )
        )
        self.assertEqual(installed["md5"], md5)
        self.assertEqual(installed["time"] > info["time"], True)
        self.assertEqual(len(font_cache.fonts), 1)
        self.assertEqual(self._files(), [md5 + ".ttf", "index.json"])

    def test_install_url(self):
        url = "https://fonts.hive.pt/colonia.ttf"
        data = build_font()
        md5 = hashlib.md5(data).hexdigest()
        self.responses[url] = data
        font_cache = colony_print.FontCache(self.path)
        info = font_cache.install(dict(name="Colonia", url=url))
        self.assertEqual(info["md5"], md5)
        self.assertEqual(info["url"], url)
        self.assertEqual(font_cache.urls, {url: md5})
        self.assertEqual(
            self.downloads, [(url, colony_print.printing.common.fonts.FONT_TIMEOUT)]
        )

        # installs the font of the (cached) URL again, with and without
        # its MD5, which doesn't download it again
        font_cache.install(dict(name="Colonia", url=url))
        font_cache.install(dict(name="Colonia", url=url, md5=md5))
        self.assertEqual(len(self.downloads), 1)

        # the same font file from another URL keeps the first URL in the
        # information of the font while both URLs are cached
        self.responses["https://mirror.hive.pt/colonia.ttf"] = data
        info = font_cache.install(
            dict(name="Colonia", url="https://mirror.hive.pt/colonia.ttf")
        )
        self.assertEqual(info["url"], url)
        self.assertEqual(
            font_cache.urls, {url: md5, "https://mirror.hive.pt/colonia.ttf": md5}
        )
        self.assertEqual(len(self.downloads), 2)

        # removes the font file from the cache (as if deleted) so that the
        # URL is downloaded again, restoring the file
        os.remove(os.path.join(self.path, md5 + ".ttf"))
        font_cache.install(dict(name="Colonia", url=url))
        self.assertEqual(len(self.downloads), 3)
        self.assertEqual(os.path.exists(os.path.join(self.path, md5 + ".ttf")), True)

    def test_install_url_invalid(self):
        url = "https://fonts.hive.pt/colonia.ttf"
        font_cache = colony_print.FontCache(self.path)

        self.responses[url] = Exception("Not Found")
        self.assertRaises(
            appier.OperationalError,
            lambda: font_cache.install(dict(name="Colonia", url=url)),
        )

        self.responses[url] = dict(error="not a font")
        self.assertRaises(
            appier.OperationalError,
            lambda: font_cache.install(dict(name="Colonia", url=url)),
        )

        self.responses[url] = b"not a font"
        self.assertRaises(
            appier.OperationalError,
            lambda: font_cache.install(dict(name="Colonia", url=url)),
        )
        self.assertEqual(font_cache.urls, {})
        self.assertEqual(self._files(), [])

        # the font of the (cached) URL doesn't match the provided MD5
        self.responses[url] = build_font()
        font_cache.install(dict(name="Colonia", url=url))
        self.assertRaises(
            appier.OperationalError,
            lambda: font_cache.install(dict(name="Colonia", url=url, md5="0" * 32)),
        )

    def test_install_md5(self):
        data = build_font(style="italic")
        md5 = hashlib.md5(data).hexdigest()
        font_cache = colony_print.FontCache(self.path)
        self.assertRaises(
            appier.OperationalError,
            lambda: font_cache.install(dict(name="Colonia", md5=md5)),
        )

        font_cache.install(dict(name="Colonia", data_b64=base64.b64encode(data)))
        info = font_cache.install(dict(name="Colonia", style="italic", md5=md5))
        self.assertEqual(info["md5"], md5)
        self.assertEqual(info["style"], "italic")
        self.assertEqual(
            font_cache.install(dict(name="Colonia", md5=md5.upper()))["md5"], md5
        )

        # the font file is removed from the cache (as if deleted) so that
        # the reference to it is no longer valid
        os.remove(os.path.join(self.path, md5 + ".ttf"))
        self.assertRaises(
            appier.OperationalError,
            lambda: font_cache.install(dict(name="Colonia", md5=md5)),
        )

    def test_install_invalid(self):
        data = build_font()
        data_b64 = base64.b64encode(data)
        font_cache = colony_print.FontCache(self.path)

        invalid = [
            dict(name="Colonia"),
            dict(name="Colonia", md5="../../index"),
            dict(name="Calibri", data_b64=data_b64),
            dict(name="Colonia", style="bold", data_b64=data_b64),
            dict(name="Colonia", md5="0" * 32, data_b64=data_b64),
            dict(name="Colonia", data_b64=base64.b64encode(b"OTTO" + data[4:])),
            dict(name="Colonia", data_b64=base64.b64encode(b"not a font")),
        ]
        for font_ in invalid:
            self.assertRaises(
                appier.OperationalError, lambda: font_cache.install(font_)
            )

        # verifies that none of the (refused) fonts was installed, not
        # even the valid font files whose name or style didn't match
        self.assertEqual(font_cache.fonts, {})
        self.assertEqual(self._files(), [])

        font_cache = colony_print.FontCache(self.path, max_size=len(data) - 1)
        self.assertRaises(
            appier.OperationalError,
            lambda: font_cache.install(dict(name="Colonia", data_b64=data_b64)),
        )
        self.assertEqual(self._files(), [])

        font_cache = colony_print.FontCache(self.path, max_size=len(data))
        font_cache.install(dict(name="Colonia", data_b64=data_b64))
        self.assertEqual(len(self._files()), 2)

    def test_install_message(self):
        font_cache = colony_print.FontCache(self.path)
        try:
            font_cache.install(dict(name="Colonia", data_b64=base64.b64encode(b"font")))
        except appier.OperationalError as exception:
            message, code = exception.message, exception.code
        self.assertEqual(message.startswith("Font 'Colonia' is not valid: "), True)
        self.assertEqual(code, 400)

        try:
            font_cache.install(
                dict(name="Calibri", data_b64=base64.b64encode(build_font()))
            )
        except appier.OperationalError as exception:
            message, code = exception.message, exception.code
        self.assertEqual(message, "Font 'Calibri' has the family name 'Colonia'")
        self.assertEqual(code, 400)

    def test_installed(self):
        font_cache = colony_print.FontCache(self.path)
        self.assertEqual(font_cache.installed(), [])

        bold = font_cache.install(
            dict(name="Colonia", data_b64=base64.b64encode(build_font(style="bold")))
        )
        time.sleep(0.01)
        regular = font_cache.install(
            dict(name="Colonia", data_b64=base64.b64encode(build_font()))
        )
        time.sleep(0.01)
        binaria = font_cache.install(
            dict(name="Binaria", data_b64=base64.b64encode(build_font(name="Binaria")))
        )

        # installs another file of the regular style of the family (as an
        # updated font) that becomes the active one for the style
        time.sleep(0.01)
        updated = font_cache.install(
            dict(name="Colonia", data_b64=base64.b64encode(build_font() + b"\0"))
        )

        installed = font_cache.installed()
        self.assertEqual(
            [(font["md5"], font["active"]) for font in installed],
            [
                (binaria["md5"], True),
                (bold["md5"], True),
                (regular["md5"], False),
                (updated["md5"], True),
            ],
        )
        self.assertEqual("path" in installed[0], False)
        self.assertEqual(installed[0]["name"], "Binaria")

        # references the older file by its MD5 that becomes the active
        # one again (the most recently installed)
        time.sleep(0.01)
        font_cache.install(dict(name="Colonia", md5=regular["md5"]))
        self.assertEqual(
            [(font["md5"], font["active"]) for font in font_cache.installed()],
            [
                (binaria["md5"], True),
                (bold["md5"], True),
                (updated["md5"], False),
                (regular["md5"], True),
            ],
        )

    def test_files(self):
        font_cache = colony_print.FontCache(self.path)
        self.assertEqual(font_cache.files(), {})

        regular = font_cache.install(
            dict(name="Colonia", data_b64=base64.b64encode(build_font()))
        )
        bold = font_cache.install(
            dict(name="Colonia", data_b64=base64.b64encode(build_font(style="bold")))
        )
        self.assertEqual(
            font_cache.files(),
            {
                ("colonia", "regular"): regular["path"],
                ("colonia", "bold"): bold["path"],
            },
        )

        time.sleep(0.01)
        updated = font_cache.install(
            dict(name="Colonia", data_b64=base64.b64encode(build_font() + b"\0"))
        )
        self.assertEqual(font_cache.files()[("colonia", "regular")], updated["path"])

    def test_active(self):
        font_cache = colony_print.FontCache(self.path)
        font_cache.fonts = dict(
            a=dict(name="Colonia", style="regular", time=2.0),
            b=dict(name="colonia", style="regular", time=3.0),
            c=dict(name="COLONIA", style="regular", time=1.0),
            d=dict(name="Colonia", style="bold", time=1.0),
        )
        self.assertEqual(
            font_cache._active(),
            {("colonia", "regular"): "b", ("colonia", "bold"): "d"},
        )

    def test_download(self):
        url = "https://fonts.hive.pt/colonia.ttf"
        font_cache = colony_print.FontCache(self.path)
        self.responses[url] = b"font"
        self.assertEqual(font_cache._download("Colonia", url), b"font")

        self.responses[url] = Exception("Connection refused")
        try:
            font_cache._download("Colonia", url)
        except appier.OperationalError as exception:
            message = exception.message
        self.assertEqual(
            message,
            "Font 'Colonia' not downloaded from '%s': Connection refused" % url,
        )

        self.responses[url] = appier.legacy.u("font")
        self.assertRaises(
            appier.OperationalError, lambda: font_cache._download("Colonia", url)
        )

    def test_file(self):
        font_cache = colony_print.FontCache(self.path)
        self.assertEqual(
            font_cache._file("a" * 32), os.path.join(self.path, "a" * 32 + ".ttf")
        )

    def test_write(self):
        font_cache = colony_print.FontCache(self.path)
        file_path = os.path.join(self.path, "file.ttf")
        font_cache._write(file_path, b"first")
        font_cache._write(file_path, b"second")
        with open(file_path, "rb") as file:
            self.assertEqual(file.read(), b"second")
        self.assertEqual(self._files(), ["file.ttf"])

        # simulates an older version of python, that is not able to
        # replace a file, so that the file is removed before
        replace = os.replace if hasattr(os, "replace") else None
        if replace:
            del os.replace
        try:
            font_cache._write(file_path, b"third")
            font_cache._write(os.path.join(self.path, "other.ttf"), b"other")
        finally:
            if replace:
                os.replace = replace
        with open(file_path, "rb") as file:
            self.assertEqual(file.read(), b"third")
        self.assertEqual(self._files(), ["file.ttf", "other.ttf"])

    def test_save(self):
        font_cache = colony_print.FontCache(self.path)
        font_cache.fonts = dict(a=dict(name="Colonia", style="regular", time=1.0))
        font_cache.urls = {"https://fonts.hive.pt/colonia.ttf": "a"}
        font_cache._save()
        with open(os.path.join(self.path, "index.json"), "rb") as file:
            index = json.loads(file.read().decode("utf-8"))
        self.assertEqual(index, dict(fonts=font_cache.fonts, urls=font_cache.urls))
