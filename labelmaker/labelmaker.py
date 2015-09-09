import math
import os
import textwrap
import zlib as z

from .util import safe_get
import labels
from reportlab.lib import units, styles
from reportlab.graphics import shapes
from reportlab.graphics.barcode import qr
from reportlab.pdfbase.pdfmetrics import stringWidth
#from reportlab.platypus import Frame, Paragraph

class DefaultLabel(object):
    """Label that places QR code (if any) at the left, lines of text (if any) on the right, and
    icons (if any) in the lower right corner."""
    # More lab safety-related icons at https://pixabay.com/en/photos/danger%20sign/
    def __init__(self, text_lines=None, text_format=None, text_shrink="wrap", 
            qr_data=None, qr_format=None, icons=None, index=None, index_format=None):
        self.text_lines = []
        if text_lines is not None:
            for i, line in enumerate(text_lines):
                fmt = {}
                if text_format is not None:
                    for k,v in text_format.iteritems():
                        fmt[k] = safe_get(v, i)
                shrink = safe_get(text_shrink, i)
                self.add_text(line, fmt, shrink)
        
        self.set_qr(qr_data, qr_format)
        self.icons = []
        if icons is not None:
            for i in icons:
                self.add_icon(i)
        
        self.set_index(index, index_format)
    
    def add_text(self, text, fmt, shrink):
        self.text_lines.append((text, fmt, shrink))
    
    def set_qr(self, qr_data, qr_format):
        self.qr_data = qr_data
        self.qr_format = qr_format or {}
    
    def add_icon(self, icon):
        assert os.path.exists(icon)
        self.icons.append(icon)
    
    def set_index(self, index, index_format):
        self.index = index
        self.index_format = index_format or {}
        self.index_format["textAnchor"] = "end"
    
    def draw(self, label, width, height):
        text_x = 0
        max_width = width
        max_height = height
        icon_size = 16
        
        qr = None
        if self.qr_data is not None:
            qr = make_qr(self.qr_data, **self.qr_format)
            label.add(qr)
            text_x = qr.barWidth + 1
            max_width -= text_x
        
        if self.index is not None:
            font_name = self.index_format.get("fontName", shapes.STATE_DEFAULTS["fontName"])
            font_size = self.index_format.get("fontSize", shapes.STATE_DEFAULTS["fontSize"])
            index_width = stringWidth(self.index, font_name, font_size)
            max_width -= (index_width + 1)
            index_x = width
            index_y = height - font_size
            label.add(shapes.String(index_x, index_y, self.index, **self.index_format))
        
        if len(self.icons) > 0:
            icon_x = width - ((icon_size + 1) * len(self.icons))
            icon_y = 1 # TODO: make this configurable
            max_height -= icon_size
            for i, icon in enumerate(self.icons):
                label.add(shapes.Image(icon_x, icon_y, icon_size, icon_size, icon))
                icon_x += icon_size + 1
        
        # Implementation using shapes.String
        text_y = height
        for text, fmt, shrink in self.text_lines:
            font_name = fmt.get("fontName", shapes.STATE_DEFAULTS["fontName"])
            font_size = fmt.get("fontSize", shapes.STATE_DEFAULTS["fontSize"])
            
            if shrink == "wrap":
                text = wrap_text(text, max_width, font_name, font_size)
                
                if (font_size * len(text)) > text_y:
                    break
                
                for text_line in text:
                    text_y -= (font_size + 1)
                    label.add(shapes.String(text_x, text_y, text_line, **fmt))
                    
            else:
                if shrink == "scale":
                    font_size = scale_font_size(text, max_width, font_name, font_size)
                    fmt["fontSize"] = font_size
                
                if font_size > text_y:
                    break
                
                text_y -= (font_size + 1)
                label.add(shapes.String(text_x, text_y, text, **fmt))
        
        # Implementation using platypus.Paragraph
        # shapes and platypus are not mixable
        #frame_width = width - text_x
        #frame_height = height - icon_size
        #text_frame = Frame(text_x, height, frame_width, frame_height, 
        #    leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0)
        #for text, fmt in self.text_lines:
        #    style = styles.ParagraphStyle("default")
        #    for attr, val in fmt.iteritems():
        #        setattr(style, attr, val)
        #    text_frame.add(Paragraph(text, style), label)
        #label.add(text_frame)

def wrap_text(text, max_width, font_name="Helvetica", font_size=50):
    text_width = stringWidth(text, font_name, font_size)
    nchar = len(text)
    new_text = [text]
    while text_width > max_width:
        nchar -= 1
        new_text = textwrap.wrap(text, nchar)
        text_width = max(stringWidth(t, font_name, font_size) for t in new_text)
    return new_text

def scale_font_size(text, max_width, font_name="Helvetica", font_size=50, scaling=0.8):
    """Measure the width of the text and shrink the font size until it fits."""
    text_width = stringWidth(text, font_name, font_size)
    while text_width > max_width:
        font_size *= scaling
        text_width = stringWidth(text, font_name, font_size)
    return font_size

def make_labels(specs, label_list, outfile, skip=0):
    """Make labels for a given set of Label objects."""
    
    # create the sheet
    # The draw function just calls Label.draw
    def draw_label(label, width, height, obj):
        if obj is not None:
            obj.draw(label, width, height)
    sheet = labels.Sheet(specs, draw_label, border=True)
    
    if skip > 0:
        cols = specs.columns
        rows = specs.rows
        labels_per_page = cols * rows
        skip = skip % labels_per_page
        partial = []
        for i in xrange(rows):
            for j in xrange(cols):
                partial.append(i+1,j+1)
                skip -= 1
                if skip <= 0:
                    break
        sheet.partial_page(1, partial)
    
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
