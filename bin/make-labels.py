#!/usr/bin/env python
# Given a csv file, create labels of different sizes that include text and a QR code.

import argparse
import csv
from decimal import Decimal
import json
import pkgutil

from labelmaker.labelmaker import *
from labelmaker.util import *
#from reportlab.lib import enums

def make_labels_from_table(reader, text_strings, qr_string, icon_column, count_column, index_string,
        outfile, config, skip=0, label_class=DefaultLabel):
    """Create one label for each row in a table.

    Keyword arguments:
    reader       -- csv reader that returns a tuple for each row of a table.
    text_string  -- tuple of strings for the lines of text on the labels.
    qr_string    -- string to be encoded in the QR code.
    icon_column  -- name of column with icons to be shown on the label.
    count_column -- name of column with count of containers
    index_string -- string showing the label index
    outfile      -- PDF file to write.
    config       -- dict with configuration information; the result of calling `get_config`
    label_class  -- Object type to create for each label; must have same constructor
                   signature as DefaultLabel
    """
    
    # Compute the number of points available for drawing/printing.
    specs = config["spec"]
    height = float(specs._label_height - (specs._top_padding + specs._bottom_padding)) * units.mm
    
    text_format = None
    text_shrink = "wrap"
    if "text" in config:
        text_format = config["text"].get("format", {})
        text_shrink = config["text"].get("shrink", "wrap")

        if "alignment" in text_format:
            # shapes version
            aln_map = dict(
                left="start",
                center="middle",
                right="end",
                justify="start" # no justify option
            )
            text_format["textAnchor"] = safe_map(lambda a: aln_map[a], text_format["alignment"])
                        
            # Platypus version
            # have to map alignment strings to enums
            #aln_map = dict(
            #    left=enums.TA_LEFT,
            #    center=enums.TA_CENTER,
            #    right=enums.TA_RIGHT,
            #    justify=enums.TA_JUSTIFY
            #)
            #text_format["alignment"] = safe_map(lambda a: aln_map[a], text_format["alignment"])
    
    if "qr" in config:
        compress = config["qr"]["compress"]
        qr_format = config["qr"].get("format", {})
        # by default, set the QR to be square, with both sides equal
        # to the usable height of the label
        if "barWidth" not in qr_format:
            qr_format["barWidth"] = qr_format.get("barHeight", height)
        if "barHeight" not in qr_format:
            qr_format["barHeight"] = qr_format["barWidth"]
    
    if "index" in config and count_column is not None:
        if index_string is None:
            index_string = config["index"].get("default", "{_index_} / {_count_}")
        index_format = config["index"].get("format", {})
    else:
        index_string = None
    
    label_list = []
    for row in reader:
        def make_label(idx):
            # Add the index varaible to the row
            row["_index_"] = i + 1
            # Get the lines of text
            text = None if text_strings is None else tuple(col.format(**row) for col in text_strings)
            # Get the data to encode in the QR code
            qr_data = None if qr_string is None else qr_string.format(**row)
            # Translate the icon codes into paths to image files
            icons = []
            if icon_column is not None and "icons" in config:
                icons = tuple(config["icons"][i] for i in row[icon_column])
            index = None if index_string is None else index_string.format(**row)
            # Create the label
            return label_class(text, text_format, text_shrink, qr_data, qr_format, icons, index, index_format)
        
        count = int(row[count_column]) if count_column is not None and count_column in row else 1
        row["_count_"] = count
        for i in xrange(count):
            label_list.append(make_label(i+1))
    
    # Generate the PDF for the labels
    make_labels(specs, label_list, outfile, skip, 
        config.get("borders", True), config.get("fontPath", None))

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
    
    if "fontPath" in label_config:
        label_config["fontPath"] = map(
            lambda path: os.path.abspath(os.path.expanduser(path)),
            label_config["fontPath"])

    return label_config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--label-config", default="config.json",
        help="Path to label config file.")
    parser.add_argument("-p", "--page-config", default=None,
        help="Path to page config file.")
    parser.add_argument("-t", "--text-strings", nargs="*", default=None,
        help="Text strings. A string is any text, with column  values substituted for "\
             "{<column name>}. Defaults to the first N columns, where N is the number "\
             "of lines specified in the config file.")
    parser.add_argument("-q", "--qr-string", default=None,
        help="String to encode in the QR code. Defaults to the first text column, or the first "\
             "column if no text columns are specified. Multiple columns can be concatenated using "\
             "the '+' sign.")
    parser.add_argument("-i", "--icon-column", default=None,
        help="Name of column in input file listing icons to display on label. Icons must be "\
             "specified as a string of one-character icon identifiers that match those defined "
             "in the config file.")
    parser.add_argument("-c", "--count-column", default=None,
        help="Name of column specifying containers with the same label; that many copies of "\
             "the label will be printed, and the index will be available as the {_index_} variable.")
    parser.add_argument("-n", "--index-string", default=None,
         help="String specifying the label index to print in the upper right of the label. "\
              "Defaults to {_index_} / {_count_}.")             
    parser.add_argument("-H", "--no-header", action="store_true", default=False,
        help="The input file has no header line; all variables will be named {col<index>} "\
             "where <index> is the (one-based) column index.")
    parser.add_argument("--delimiter", default=",",
        help="Input file delimiter.")
    parser.add_argument("--sheet", default=1,
        help="Worksheet name or index, if --workbook is specified.")
    parser.add_argument("--skip", type=int, default=0,
        help="Number of labels to skip (e.g. because they've already been used)")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-f", "--infile",
        help="Text input file (CSV unless --delimiter is specified).")
    input_group.add_argument("-x", "--workbook",
        help="Excel input file (first sheet is loaded unless --sheet is specified).")
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
    
    text_strings = None
    if config["text"] and config["text"]["lines"] > 0:
        if args.text_strings is None:
            text_strings = list("{{col{0}}}".format(i+1) for i in xrange(config["text"]["lines"]))
        else:
            text_strings = args.text_strings
            assert len(text_strings) == config["text"]["lines"]
    
    qr_string = None
    if config["qr"]:
        qr_string = args.qr_string or text_strings[0] if text_strings is not None else "{col1}"
    
    header = not args.no_header
    if args.infile:    
        reader = AliasedDictReader(args.infile, header,
            delimiter=args.delimiter, skipinitialspace=True)
    else:
        date_format = config.get("dateFormat", "%Y-%m-%d")
        reader = ExcelReader(args.workbook, args.sheet, header, date_format)
    
    try:
        make_labels_from_table(reader, text_strings, qr_string, args.icon_column, 
            args.count_column, args.index_string, args.outfile, config)
    
    finally:
        reader.close()

if __name__ == "__main__":
    main()
