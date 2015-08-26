#!/usr/bin/env python
# Given a csv file, create labels of different sizes that include text and a QR code.
# Dependencies:
# pip install reportlab
# pip install pylabels

import argparse
import csv
from decimal import Decimal
import json
import math
import zlib as z

import labels
from reportlab.lib import units
from reportlab.graphics import shapes
from reportlab.graphics.barcode import qr

class Column(object):
    def __init__(self, col):
        self.idxs = map(int, col.split("+"))
    
    def get(self, row, delim=", "):
        return delim.join(list(row[i] for i in self.idxs))

class Label(object):
    def __init__(self, text_lines=None, text_format=None, qr_data=None, qr_format=None):
        self.text_lines = []
        if text_lines is not None:
            for i in xrange(len(text_lines)):
                fmt = {}
                if text_format is not None:
                    for k,v in text_format.iteritems():
                        if isinstance(v, tuple) or isinstance(v, list):
                            fmt[k] = v[i]
                        else:
                            fmt[k] = v
                self.add_text(text_lines[i], fmt)
        
        self.set_qr(qr_data, qr_format)
    
    def add_text(self, text, fmt):
        self.text_lines.append((text, fmt))
    
    def set_qr(self, qr_data, qr_format):
        self.qr_data = qr_data
        self.qr_format = qr_format
    
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

def make_labels_from_table(reader, text_columns, qr_column, outfile, config):
    specs = config["spec"]
    height = float(specs._label_height - (specs._top_padding + specs._bottom_padding)) * units.mm
    
    text_format = None
    if "text" in config:
        text_format = config["text"].get("format", {})
    
    if "qr" in config and config["qr"]:
        qr_format = confg["qr"] if isinstance(config["qr"], dict) else {}
        if "barWidth" not in qr_format:
            qr_format["barWidth"] = qr_format.get("barHeight", height)
        if "barHeight" not in qr_format:
            qr_format["barHeight"] = qr_format["barWidth"]
    
    label_list = []
    for row in reader:
        text = None if text_columns is None else tuple(col.get(row) for col in text_columns)
        qr_data = None if qr_column is None else qr_column.get(row)
        label_list.append(Label(text, text_format, qr_data, qr_format))
    
    make_labels(label_list, outfile, specs)

def make_labels(label_list, outfile, specs=None):
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

def get_config(config_file, specs_file):
    with open(specs_file, "rU") as i:
        specs = json.load(i)
    with open(config_file, "rU") as i:
        config = json.load(i)
    
    spec_config = config["spec"]
    page_type, spec_args = specs["label"][spec_config["name"]]
    spec_args["sheet_width"], spec_args["sheet_height"] = specs["page"][page_type]
    for side in ('top','bottom','left','right'):
        key = "{0}_padding".format(side)
        if key in spec_config:
            spec_args[key] = spec_config[key]
    spec_args = dict((k, Decimal(v)) for k,v in spec_args.items())
    spec = labels.Specification(**spec_args)
    config["spec"] = spec
    
    text = False
    if "text" in config:
        text = config["text"]
        if "lines" not in text:
            text["lines"] = 1
    config["text"] = text
    
    return config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json",
        help="Path to config file")
    parser.add_argument("--specs", default="specs.json",
        help="Path to label specs file")
    parser.add_argument("--text-columns", default=None,
        help="Column indices of input file to use for text on labels. Defaults to the "\
             "first N columns, where N is the number of lines specified in the config file. "\
             "Multiple columns can be concatenated using the '+' sign.")
    parser.add_argument("--qr-column", default=None,
        help="Column index of input file to encode in the QR code. Defaults to the first "\
             "text column, or the first column if no text columns are specified. "\
             "Multiple columns can be concatenated using the '+' sign.")
    parser.add_argument("-i", "--infile", required=True)
    parser.add_argument("-o", "--outfile", required=True)
    args = parser.parse_args()
    
    config = get_config(args.config, args.specs)
    
    text_columns = None
    if config["text"] and config["text"]["lines"] > 0:
        if args.text_columns is None:
            text_columns = list(Column(i) for i in range(config["text"]["lines"]))
        else:
            text_columns = map(Column, args.text_columns.split(","))
            assert len(text_columns) == config["text"]["lines"]
    
    qr_column = None
    if config["qr"]:
        if args.qr_column is None:
            qr_column = text_columns[0] if text_columns is not None else 0
        else:
            qr_column = Column(args.qr_column)
    
    with open(args.infile, "rU") as i:
        make_labels_from_table(csv.reader(i), text_columns, qr_column, args.outfile, config)
    
if __name__ == "__main__":
    main()
