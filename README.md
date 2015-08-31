# Label generator

This is a simple program to generate labels from a table (CSV file).

## Dependencies

```python
pip install reportlab
pip install pylabels
```

## Installation

```python
pip install git+git://github.com/jdidion/labels.git
```

## Inputs

There are three required inputs:

1. Label config
2. Page config
3. CSV file

### Label config file

Defines how things should be laid out on each label. Importantly, this does not include any information about the layout of the page of labels (this is in the page config).

The label config files are in JSON format. An example can be found in examples/config.json.

The label config file has three sections: spec, text, and qr. The first is required, and at a minimum gives the name of the page spec (corresponding to a page spec defined in the page config file). 

The text section defines the number of text lines, and properties of each line (such as font name, font size, and justification). 

If the qr section is present, a QR code will be included on the label. You can also provide formatting parameters for the QR code.

### Page config file

Describes the layout of a page of labels. This config file is also in JSON format, and an example can be found in config/specs.json. 

There are three sections: page, label, and icon. A page config is an array of two numbers - the width and height of the page. Examples of page types are A4 and Letter. 

The label section defines parameters for each label layout. Each label type is an array, with the first item being the page type (corresponding to a page type defined in the page section), and the second item is a dictionary. Various parameters can be defined, such as the numbers of label columns and rows, the height and width of each label, the types of corners, the spacing in between labels, and the page margins. All measurements must be in mm.

The icon section maps one-character codes to image file paths. These are icons that can be displayed on labels.

### CSV file

The format of the CSV file is arbitrary - as long as it is valid CSV, it will work with this program. You need to identify the indices (counting from zero) of the columns that you wish to appear as text (if any), and those that you wish to be encoded in a QR code (if any). Optionally, you can also have a column with icon identifiers, which correspond to those defined in the specs file.

Example input file:

<pre>
Name, Sex, Birthday, URL,             Icons
John, M,   May 24,   http://john.com, C
Jane, F,   Jan 7,    http://fred.org, CP
</pre>

## Usage

From this above input file, we may want to create a label laid out as follows:

<pre>
------------------------------
| ------  Name, Sex          |
| | QR |  Birthday           |
| |    |                     |
| ------      Fav. food Icons|
------------------------------
</pre>

Using the default page and label configurations provided in the example files, we could create this label with the following command:

```python
python make-labels.py --text-columns 0+1,2 --qr-column 3 --icon-column 4
```
