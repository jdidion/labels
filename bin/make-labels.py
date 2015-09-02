#!/usr/bin/env python
# Given a csv file, create labels of different sizes that include text and a QR code.

import argparse
import csv
from decimal import Decimal
import json
import pkgutil

from labelmaker.labelmaker import *

class Column(object):
    """Represents one or more columns in a table. The `get` function will always
    return the contents of the column(s) concatenated into a single string."""
    
    def __init__(self, col):
        if isinstance(col, str):
            self.idxs = map(int, col.split("+"))
        else:
            self.idxs = (col,)
    
    def get(self, row, delim=", "):
        return delim.join(list(row[i] for i in self.idxs))

def make_labels_from_table(reader, text_columns, qr_column, icon_column, outfile, config, label_class=DefaultLabel):
    """Create one label for each row in a table.

    Keyword arguments:
    reader      -- csv reader that returns a tuple for each row of a table.
    text_column -- tuple of Column objects for the lines of text on the labels.
    qr_column   -- Column object for the data to be encoded in the QR code.
    icon_column -- Column object for the icons to be shown on the label.
    outfile     -- PDF file to write.
    config      -- dict with configuration information; the result of calling `get_config`
    """
    
    # Compute the number of points available for drawing/printing.
    specs = config["spec"]
    height = float(specs._label_height - (specs._top_padding + specs._bottom_padding)) * units.mm
    
    text_format = None
    if "text" in config:
        text_format = config["text"].get("format", {})
    
    if "qr" in config:
        compress = config["qr"]["compress"]
        qr_format = config["qr"].get("format", {})
        # by default, set the QR to be square, with both sides equal
        # to the usable height of the label
        if "barWidth" not in qr_format:
            qr_format["barWidth"] = qr_format.get("barHeight", height)
        if "barHeight" not in qr_format:
            qr_format["barHeight"] = qr_format["barWidth"]
    
    label_list = []
    for row in reader:
        # Get the lines of text
        text = None if text_columns is None else tuple(col.get(row) for col in text_columns)
        # Get the data to encode in the QR code
        qr_data = None if qr_column is None else qr_column.get(row)
        # Translate the icon codes into paths to image files
        icons = []
        if icon_column is not None and "icons" in config:
            icons = tuple(config["icons"][i] for i in icon_column.get(row))
        # Create the label
        label_list.append(label_class(text, text_format, qr_data, qr_format, icons))
    
    # Generate the PDF for the labels
    make_labels(specs, label_list, outfile)

def prepare_config(label_config, page_config):
    """Prepare configuration information from two JSON config files: labels and specs.
    
    Keyword arguments:
    label_config -- JSON file with configuration information 
                    for a specific set of labels.
    page_config  -- JSON file with configuration information 
                    with layouts of standard label types.
    """
    # TODO: exceptions will be raised if any expected keys are missing;
    # do explicit validation and raise custom exceptions
    
    # The 'spec' config entry tells us which spec to use
    spec_config = label_config["spec"]
    # Select the requested spec from the spec config
    page_type, spec_args = page_config["label"][spec_config["name"]]
    # Resolve the page type into width and height
    spec_args["sheet_width"], spec_args["sheet_height"] = page_config["page"][page_type]
    # Padding may be specified in the config; if so, transfer to the spec
    for side in ('top','bottom','left','right'):
        key = "{0}_padding".format(side)
        if key in spec_config:
            spec_args[key] = spec_config[key]
    # Convert all spec values to arbitrary precision, to prevent
    # rounding errors
    spec_args = dict((k, Decimal(v)) for k,v in spec_args.items())
    spec = labels.Specification(**spec_args)
    label_config["spec"] = spec
    
    text = False
    if "text" in label_config:
        text = label_config["text"]
        if "lines" not in text:
            # Use one line of text by default
            text["lines"] = 1
    label_config["text"] = text
    
    qr = False
    if "qr" in label_config:
        qr = label_config["qr"]
        if "compress" not in qr:
            # Do not compress QR code data by default
            qr["compress"] = False
    label_config["qr"] = qr
    
    return label_config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--label-config", default="config.json",
        help="Path to label config file.")
    parser.add_argument("-p", "--page-config", default=None,
        help="Path to page config file.")
    parser.add_argument("-t", "--text-columns", default=None,
        help="Comma-delimited list of column indices of input file to use for text on labels. "
             "Defaults to the first N columns, where N is the number of lines specified in the "
             "config file. Multiple columns can be concatenated using the '+' sign.")
    parser.add_argument("-q", "--qr-column", default=None,
        help="Column index of input file to encode in the QR code. Defaults to the first "\
             "text column, or the first column if no text columns are specified. "\
             "Multiple columns can be concatenated using the '+' sign.")
    parser.add_argument("-i", "--icon-column", default=None,
        help="Column index of input file listing icons to display on label. Icons must be "\
             "specified as a string of one-character icon identifiers that match those defined "
             "in the specs file.")
    parser.add_argument("-H", "--header", action="store_true", default=False,
        help="The input file has a header line.")
    parser.add_argument("--delimiter", default=",",
        help="Input file delimiter.")
    parser.add_argument("-f", "--infile", required=True)
    parser.add_argument("-o", "--outfile", required=True)
    args = parser.parse_args()
    
    with open(args.label_config, "rU") as i:
        label_config = json.load(i)
    
    if args.page_config is None:
        page_config = json.loads(pkgutil.get_data("labelmaker", "config/page-config.json"))
    else:
        with open(args.page_config, "rU") as i:
            page_config = json.load(i)
    
    config = prepare_config(label_config, page_config)
    
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
        reader = csv.reader(i, delimiter=args.delimiter, skipinitialspace=True)
        if args.header:
            # TODO: capture the header and use it to enable
            # the user to specify columns by name rather than
            # index
            reader.next()
        make_labels_from_table(reader, text_columns, qr_column, icon_column, args.outfile, config)
    
if __name__ == "__main__":
    main()
