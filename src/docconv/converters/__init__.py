"""Converters package: imports all built-in converters to register them."""

from docconv.converters.base import BaseConverter
from docconv.converters.docx import DocxConverter
from docconv.converters.epub import EpubConverter
from docconv.converters.html import HtmlConverter
from docconv.converters.image import ImageConverter
from docconv.converters.pdf import PdfConverter
from docconv.converters.pptx import PptxConverter
from docconv.converters.text import TextConverter
from docconv.converters.xlsx import XlsxConverter

__all__ = [
    "BaseConverter",
    "DocxConverter",
    "EpubConverter",
    "HtmlConverter",
    "ImageConverter",
    "PdfConverter",
    "PptxConverter",
    "TextConverter",
    "XlsxConverter",
]
