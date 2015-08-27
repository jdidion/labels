import math
import os
import zlib as z

import labels
from reportlab.lib import units
from reportlab.graphics import shapes
from reportlab.graphics.barcode import qr

class DefaultLabel(object):
    """Label that places QR code (if any) at the left, lines of text (if any) on the right, and
    icons (if any) in the lower right corner."""
    def __init__(self, text_lines=None, text_format=None, qr_data=None, qr_format=None, icons=None):
        self.text_lines = []
        if text_lines is not None:
            for i, line in enumerate(text_lines):
                fmt = {}
                if text_format is not None:
                    for k,v in text_format.iteritems():
                        if isinstance(v, tuple) or isinstance(v, list):
                            fmt[k] = v[i]
                        else:
                            fmt[k] = v
                self.add_text(line, fmt)
        
        self.set_qr(qr_data, qr_format)
        self.icons = []
        if icons is not None:
            for i in icons:
                self.add_icon(i)
    
    def add_text(self, text, fmt):
        self.text_lines.append((text, fmt))
    
    def set_qr(self, qr_data, qr_format):
        self.qr_data = qr_data
        self.qr_format = qr_format
    
    def add_icon(self, icon):
        assert os.path.exists(icon)
        self.icons.append(icon)
    
    def draw(self, label, width, height):
        text_x = 0
        
        qr = None
        if self.qr_data is not None:
            qr = make_qr(self.qr_data, **self.qr_format)
            label.add(qr)
            text_x = qr.barWidth + 1
        
        text_y = height
        for text, fmt in self.text_lines:
            font_size = fmt.get("fontSize", shapes.STATE_DEFAULTS["fontSize"])
            text_y -= (font_size + 1)
            label.add(shapes.String(text_x, text_y, text, **fmt))
        
        icon_size = 16
        icon_x = width - ((icon_size + 1) * len(self.icons))
        icon_y = 1 # TODO: make this configurable
        for i, icon in enumerate(self.icons):
            label.add(shapes.Image(icon_x, icon_y, icon_size, icon_size, icon))
            icon_x += icon_size + 1

def make_labels(specs, label_list, outfile):
    """Make labels for a given set of Label objects."""
    
    # create the sheet
    # The draw function just calls Label.draw
    def draw_label(label, width, height, obj):
        obj.draw(label, width, height)
    sheet = labels.Sheet(specs, draw_label, border=True)
    
    # add labels
    sheet.add_labels(label_list)

    # Save the file and we are done.
    sheet.save(outfile)

def make_qr(data, error="L", version=None, compress=None, **kwargs):
    """Encode data and generate a QR code. By default, the smallest possible code is
    created, and gzip compression is used if the data is smaller when compressed."""
    
    # compress if requested
    if compress != False:
        compressed = z.compress(data, 9)
        if compress == True or len(compressed) < len(data):
            data = compressed
    
    # create QR code
    # this may raise an error if the specified version is too
    # low to accomodate the data/error combination
    return qr.QrCodeWidget(data, barLevel=error, qrVersion=version, **kwargs)
