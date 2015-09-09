# Label generator

This is a simple program to generate labels from a table (CSV file).

## Dependencies

```python
pip install reportlab
pip install pylabels
pip install openpyxl
```

Notes: 

* pylabels 1.2.0 and earlier can throw exceptions due to rounding errors. This has been fixed in the source (https://github.com/bcbnz/pylabels), so until the next version of pylabels is released, you need to install it from GitHub:
* openpyxl is only required if you want to be able to read data from excel files

```
pip install git+git://github.com/bcbnz/pylabels.git
```

## Installation

```
pip install git+git://github.com/jdidion/labels.git
```

## Inputs

There are three required inputs:

1. Label config
2. Page config
3. CSV or Excel file

### Label config file

Defines how things should be laid out on each label. Importantly, this does not include any information about the layout of the page of labels (this is in the page config).

The label config files are in JSON format. An example can be found in examples/config.json.

The label config file has four sections: spec, text, qr, index, and icons. The first is required, and at a minimum gives the name of the page spec (corresponding to a page spec defined in the page config file). 

The text section defines the number of text lines, and properties of each line (such as font name, font size, and justification). Each property can be a single value (which applies to all text lines) or an array with length equal to the number of lines.

If the qr section is present, a QR code will be included on the label. You can also provide formatting parameters for the QR code.

The index section defines the format of the index text. Index text is used when you have a label that applies to multiple physical objects (for example, 5 aliquots of the same reagent). Each label will be identical, save for the index label (by default, in the upper right corner of the label). By default, the format is "{\_index\_}/{\_count\_}", where \_index\_ and \_count\_ are two special.

The icons section maps one-character codes to image file paths. These are icons that can be displayed on labels.

You can also provide a default date format, if you are using Excel input and any columns are dates.

### Page config file

Describes the layout of a page of labels. This config file is also in JSON format, and an example can be found in config/specs.json. 

There are two sections: page and label. A page config is an array of two numbers - the width and height of the page. Examples of page types are A4 and Letter. 

The label section defines parameters for each label layout. Each label type is an array, with the first item being the page type (corresponding to a page type defined in the page section), and the second item is a dictionary. Various parameters can be defined, such as the numbers of label columns and rows, the height and width of each label, the types of corners, the spacing in between labels, and the page margins. All measurements must be in mm.

### CSV/Excel file

The format of the file is arbitrary - as long as it is valid, it will work with this program. You need to identify the indices (counting from zero) of the columns that you wish to appear as text (if any), and those that you wish to be encoded in a QR code (if any). You can also have a column with icon identifiers, which correspond to those defined in the specs file. Finally, you can have a column with the label count. Any row with count > 1 will have multiple labels printed and the index (e.g. 1/5) in the upper right corner.

Example input file:

<pre>
Name, Sex, Birthday, URL,             Icons, Count
John, M,   May 24,   http://john.com, C,     3
Jane, F,   Jan 7,    http://fred.org, CP,    1
Jim,  M,   Oct 4,    http://jim.net,  P,     2
</pre>

## Usage

From this above input file, we may want to create a label laid out as follows:

<pre>
------------------------------
| ------  Name, Sex     (1/3)|
| | QR |  Birthday           |
| |    |                     |
| ------      Fav. food Icons|
------------------------------
</pre>

Using the default page and label configurations provided in the example files, we could create this label with the following command:

```
make-labels.py -l examples/label-config.json -t "{Name}, {Sex}" "{Birthday}" -q "{URL}" \
    -c "Count" -f examples/example.csv -o labels.pdf
```

Notice that you can construct arbitrary strings and include information from the input file using variables (enclosed in curly braces) corresponding to the column names. You can also refer to columns by index (e.g. "{col3}").
