from io import StringIO
from itertools import chain
from xml.etree import ElementTree

from ._pretty_xml import WritePrettyXMLElement


class XmlFactory(object):
    """
    Fast and easy XML creation class.

    This class provides a simple a fast way of creating XML files in Python. It tries to deduce as
    much information as possible, creating intermediate elements as necessary.

    Example:
        xml = XmlFactory('root')

        xml['alpha/bravo/charlie'] # Create intermediate nodes
        xml['alpha/bravo.one'] # Create attribute on "alpha/bravo" tag
        xml['alpha/delta'] = 'XXX' # Create delta tag with text

        xml.Write('filename.xml') # Always write with a pretty XML format
    """

    def __init__(self, root_element):
        """
        :type root_element: str | Element
        :param root_element:
        """
        if isinstance(root_element, str):
            self.root = ElementTree.Element(root_element)
        elif isinstance(root_element, ElementTree.Element):
            self.root = root_element
        else:
            raise TypeError(
                "Unknown root_element parameter type: %s" % type(root_element)
            )

    def __setitem__(self, name, value):
        """
        Create a new element or attribute:

        :param unicode name:
            A XML path including or not an attribute definition

        :param unicode value:
            The value to associate with the element or attribute

        :returns Element:
            Returns the element created.
            If setting an attribute value, returns the owner element.

        @examples:
            xml['alpha/bravo'] = 'XXX' # Create bravo tag with 'XXX' as text contents
            xml['alpha.class'] = 'CLS' # Create alpha with the attribute class='CLS'
        """
        if "@" in name:
            element_name, attr_name = name.rsplit("@")
            result = self._ObtainElement(element_name)
            result.attrib[attr_name] = str(value)
        else:
            result = self._ObtainElement(name)
            result.text = str(value)
        return XmlFactory(result)

    def __getitem__(self, name):
        """
        Create and returns xml element.

        :param unicode name:
            A XML path including or not an attribute definition.

        :rtype: Element
        :returns:
            Returns the element created.
        """
        assert "@" not in name, 'The "at" (@) is used for attribute definitions'
        result = self._ObtainElement(name)
        return XmlFactory(result)

    def _ObtainElement(self, name):
        """
        Create and returns a xml element with the given name.

        :param unicode name:
            A XML path including. Each sub-client tag separated by a slash.
            If any of the parts ends with a "+" it creates a new sub-element in that part even if
            it already exists.
        """
        parent = self.root
        if name == "":
            # On Python 2.7 parent.find('') returns None instead of the parent itself
            result = parent
        else:
            parts = name.split("/")
            for i_part in parts:
                if i_part.endswith("+"):
                    i_part = i_part[:-1]
                    result = ElementTree.SubElement(parent, i_part)
                else:
                    result = parent.find(i_part)
                    if result is None:
                        result = ElementTree.SubElement(parent, i_part)
                parent = result
        return result

    def Print(self, oss=None, xml_header=False):
        """
        Prints the resulting XML in the stdout or the given output stream.

        :type oss: file-like object | None
        :param oss:
            A file-like object where to write the XML output. If None, writes the output in the
            stdout.
        """

        if oss is None:
            import sys

            oss = sys.stdout

        if xml_header:
            oss.write('<?xml version="1.0" ?>\n')
        WritePrettyXMLElement(oss, self.root)

    def GetContents(self, xml_header=False):
        """
        Returns the resulting XML.

        :return unicode:
        """
        oss = StringIO()
        self.Print(oss, xml_header=xml_header)
        return oss.getvalue()

    def AsDict(self):
        """
        Returns the data-structure as dict.

        :return dict:
        """

        def _elem2list(elem, return_children=False):
            """
            Copied from:
                https://github.com/knadh/xmlutils.py/blob/master/xmlutils/xml2json.py
            """
            block = {}

            # get the element's children
            if elem:
                cur = list(map(_elem2list, elem))

                # create meaningful lists
                scalar = False
                try:
                    if (
                        elem[0].tag != elem[1].tag
                    ):  # [{a: 1}, {b: 2}, {c: 3}] => {a: 1, b: 2, c: 3}
                        cur = dict(chain(*(d.items() for d in cur)))
                    else:
                        scalar = True
                except Exception as e:  # [{a: 1}, {a: 2}, {a: 3}] => {a: [1, 2, 3]}
                    scalar = True

                if scalar:
                    if len(cur) > 1:
                        cur = {
                            elem[0].tag: [
                                list(e.values())[0]
                                for e in cur
                                if list(e.values())[0] is not None
                            ]
                        }
                    else:
                        cur = {elem[0].tag: list(cur[0].values())[0]}

                block[elem.tag] = cur
                if return_children:
                    return cur
            else:
                val = None
                if elem.text:
                    val = elem.text.strip()
                    val = val if len(val) > 0 else None

                block[elem.tag] = val

            return block

        return _elem2list(self.root, return_children=True)

    def AsJson(self):
        """
        Returns the data-structure as a JSON.

        :return unicode:
        """
        import json

        return json.dumps(self.AsDict())
