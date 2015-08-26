#!/usr/bin/env python
# Given a csv file, create labels of different sizes that include text and a QR code.
# Depends on pylabels.

import argparse
import csv
import labels
import zlib as z
from reportlab.graphics import shapes
from reportlab.graphics.barcode import qr

# Pre-defined specifications based on product numbers from onlinelabels.com.
# These all use internal padding of 1 mm.
SPECS=dict(
    OL875=labels.Specification(215.9, 279.4, 3, 10, 66.68, 25.4, 
        top_margin=12.7, bottom_margin=12.7, left_margin=5.58, right_margin=5.58,
        column_gap=3.56, row_gap=0, corner_radius=3.18,
        top_padding=1, bottom_padding=1, left_padding=1, right_padding=1)
)

class Label(object):
    def __init__(self, text_lines=None, text_formats=None, qr_data=None, qr_format=None):
        self.text_lines = []
        if text_lines is not None:
            if isinstance(text_lines, str):
                add_text(test_lines, text_formats)
            else:
                for i in xrange(len(text_lines)):
                    fmt = None
                    if text_formats is not None:
                        if isinstance(text_formats, dict):
                            fmt = text_formats
                        else:
                            fmt = text_formats[i]
                    add_text(text_lines[i], fmt)
        
        self.qr_data = qr_data
        self.qr_format = qr_format
    
    def add_text(self, text, fmt):
        self.text_lines.append((text, fmt))
    
    def draw(self, label, width, height, qr_pos):
        objs = []
        
        for text, fmt in self.text_lines:
            
            shapes.String(2, 2, str(obj), fontName="Helvetica", fontSize=40)
        
        if self.qr_data is not None:
            fmt = self.qr_format or {}
            qr_code = make_qr(self.qr_data, **fmt)
            if qr_pos == "left":
                objs = [qr_code] + objs
            else:
                objs.append(qr_code)
        
        for o in objs:
            label.add(o)

def make_labels_from_table(reader, text_columns, qr_column, outfile, text_format=None, 
        qr_format=None, specs=None, qr_pos="left", **kwargs):
    label_list = []
    for row in reader:
        text = None if text_columns is None else tuple(row[i] for i in text_columns)
        qr_data = None if qr_column is None else row[qr_column]
        label_list.append(Label(text, text_format, qr_data, qr_format))
    make_labels(label_list, outfile, specs, qr_pos, **kwargs)

def make_labels(label_list, outfile, specs=None, qr_pos="left", **kwargs):
    """Make labels for a given set of Label objects."""
    
    # create the sheet
    if specs is None:
        specs = label.Specification(**kwargs)
    
    # The draw function just calls Label.draw
    def draw_label(label, width, height, obj):
        obj.draw(label, width, height, qr_pos)
    
    sheet = labels.Sheet(specs, draw_label, border=False)
    
    # add labels
    sheet.add_labels(label_list)

    # Save the file and we are done.
    sheet.save(outfile)

def make_qr(data, error="L", version=None, compress=None):
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
    return qr.QrCode(data, qrLevel=error, qrVersion=version)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-columns", default=None)
    parser.add_argument("--text-format", nargs="+", default=[])
    parser.add_argument("--qr-column", type=int, default=None)
    parser.add_argument("--qr-format", nargs="+", default=[])
    parser.add_argument("--noqr", action="store_true", default=False)
    parser.add_argument("--specs", default="OL875")
    parser.add_argument("--qr-pos", choices=("left", "right"), default="left")
    parser.add_argument("infile")
    parser.add_argument("outfile")
    args = parser.parse_args()
    
    specs = SPECS[args.specs]
    
    qr_column = None
    if not args.noqr:
        qr_column = args.qr_column or 0
    text_columns = None
    if args.text_columns is not None:
        text_columns = map(int, args.text_columns.split(","))
    elif qr_column is None:
        text_columns = (0,)
        
    text_format = dict((k,v) for x in args.text_format for k,v in x.split("="))
    qr_format = dict((k,v) for x in args.qr_format for k,v in x.split("="))
    
    with open(args.infile, "rU") as i:
        make_labels_from_table(csv.reader(i), text_columns, qr_column, 
            args.outfile, text_format=text_format, qr_format=qr_format,
            specs=specs, qr_pos=args.qr_pos)
    
if __name__ == "__main__":
    main()
