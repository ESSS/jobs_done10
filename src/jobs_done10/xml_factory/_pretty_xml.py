from xml.etree import ElementTree


def WritePrettyXML(input, output):
    """
    Writes the input file in pretty xml.

    :type input: unicode or file
    :param input:
        The input filename or file object.

    :type output: unicode or file
    :param output:
        The output filename or file opened for writing.
    """
    if isinstance(output, str):
        out_stream = file(output, "w")
        close_output = True
    else:
        out_stream = output
        close_output = False
    try:
        tree = ElementTree.parse(input)  # @UndefinedVariable
        WritePrettyXMLElement(out_stream, tree.getroot())
    finally:
        if close_output:
            out_stream.close()


def WritePrettyXMLElement(oss, element, indent=0):
    """
    Writes an xml element in the given file (oss) recursivelly, in pretty xml.

    :param file oss:
        The output file to write

    :param Element element:
        The Element instance (ElementTree)

    :param int indent:
        The level of indentation to write the tag.
        This is used internally for pretty printing.
    """
    from xml.sax.saxutils import escape

    INDENT = "  "

    # Start tag
    oss.write(INDENT * indent + "<%s" % element.tag)
    for i_name, i_value in sorted(element.attrib.items()):
        oss.write(' %s="%s"' % (i_name, escape(i_value)))

    if len(element) == 0 and element.text is None:
        oss.write("/>")
        return

    oss.write(">")

    # Sub-elements
    for i_element in element:
        oss.write("\n")
        WritePrettyXMLElement(oss, i_element, indent + 1)

    # Text
    if element.text is not None:
        # "&#xd;" is the hexadecimal xml entity for "\r".
        oss.write(escape(element.text, {"\r": "&#xd;"}))

    # End tag
    if element.text is None:
        oss.write("\n" + INDENT * indent)
    oss.write("</%s>" % element.tag)
