#!/usr/bin/env python
# Given a csv file, create labels of different sizes that include text and a QR code.
# Dependencies:
# pip install reportlab
# pip install pylabels

import argparse
import csv
from decimal import Decimal
import json

from labelmaker.labelmaker import *

class Column(object):
    def __init__(self, col):
        self.idxs = map(int, col.split("+"))
    
    def get(self, row, delim=", "):
        return delim.join(list(row[i] for i in self.idxs))

def make_labels_from_table(reader, text_columns, qr_column, icon_column, outfile, config):
    specs = config["spec"]
    height = float(specs._label_height - (specs._top_padding + specs._bottom_padding)) * units.mm
    
    text_format = None
    if "text" in config:
        text_format = config["text"].get("format", {})
    
    if "qr" in config:
        compress = config["qr"]["compress"]
        qr_format = config["qr"].get("format", {})
        if "barWidth" not in qr_format:
            qr_format["barWidth"] = qr_format.get("barHeight", height)
        if "barHeight" not in qr_format:
            qr_format["barHeight"] = qr_format["barWidth"]
    
    label_list = []
    for row in reader:
        text = None if text_columns is None else tuple(col.get(row) for col in text_columns)
        qr_data = None if qr_column is None else qr_column.get(row)
        icons = []
        if icon_column is not None and "icons" in config:
            icons = tuple(config["icons"][i] for i in icon_column.get(row))
        label_list.append(DefaultLabel(text, text_format, qr_data, qr_format, icons))
    
    make_labels(specs, label_list, outfile)

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
    
    qr = False
    if "qr" in config:
        qr = config["qr"]
        if "compress" not in qr:
            qr["compress"] = False
    config["qr"] = qr
    
    config["icons"] = specs.get("icon", {})
    
    return config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json",
        help="Path to config file")
    parser.add_argument("--specs", default="config/specs.json",
        help="Path to label specs file")
    parser.add_argument("--text-columns", default=None,
        help="Column indices of input file to use for text on labels. Defaults to the "\
             "first N columns, where N is the number of lines specified in the config file. "\
             "Multiple columns can be concatenated using the '+' sign.")
    parser.add_argument("--qr-column", default=None,
        help="Column index of input file to encode in the QR code. Defaults to the first "\
             "text column, or the first column if no text columns are specified. "\
             "Multiple columns can be concatenated using the '+' sign.")
    parser.add_argument("--icon-column", default=None,
        help="Column index of input file listing icons to display on label. Icons must be "\
             "specified as a string of one-character icon identifiers.")
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
    
    icon_column = Column(args.icon_column) if args.icon_column is not None else None
    
    with open(args.infile, "rU") as i:
        make_labels_from_table(csv.reader(i), text_columns, qr_column, icon_column, args.outfile, config)
    
if __name__ == "__main__":
    main()
