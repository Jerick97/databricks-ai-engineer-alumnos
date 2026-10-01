"""Narrow transport signature compatibility; preserves every original byte.

Observed SBS00771 has CRLF before %PDF-. Permit <=32 bytes of ASCII PDF
whitespace, optionally one initial UTF-8 BOM, then an actual PDF header.
Parser sees a bounded logical PDF origin; strict structural validation remains.
Stored bytes/hashes are unchanged, and no non-strict parser fallback is used.
"""
import io
import os
import re
from pypdf import PdfReader


def pdf_header_offset(content):
    if not isinstance(content,bytes):raise ValueError('PDF_INVALID')
    marker=content.find(b'%PDF-',0,38)
    if not 0<=marker<=32:raise ValueError('PDF_INVALID')
    prefix=content[:marker]
    if prefix.startswith(b'\xef\xbb\xbf'):prefix=prefix[3:]
    if any(c not in b' \t\r\n\f' for c in prefix):raise ValueError('PDF_INVALID')
    if not re.match(rb'%PDF-[12]\.[0-9](?:\r|\n| |\t)',content[marker:marker+10]):raise ValueError('PDF_INVALID')
    return marker


class _PDFOriginView(io.BytesIO):
    """Read-only parser coordinate view; retained buffer is the full original.

    The observed producer's xref offsets use %PDF as origin, not transport CRLF.
    No bytes are edited or republished; seek/tell translate that bounded origin.
    """
    def __init__(self,content,offset):
        super().__init__(content);self.offset=offset;self.seek(0)
    def seek(self,position,whence=os.SEEK_SET):
        result=super().seek(position+self.offset if whence==os.SEEK_SET else position,whence)
        return result-self.offset
    def tell(self):return super().tell()-self.offset


def strict_pdf_reader(content):
    offset=pdf_header_offset(content)
    stream=_PDFOriginView(content,offset) if offset else io.BytesIO(content)
    return PdfReader(stream,strict=True)
