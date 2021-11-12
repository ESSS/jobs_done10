from io import StringIO
from textwrap import dedent
from xml.etree import ElementTree

import pytest

from jobs_done10.xml_factory import WritePrettyXML
from jobs_done10.xml_factory import WritePrettyXMLElement
from jobs_done10.xml_factory import XmlFactory


class Test(object):
    def testSimplest(self):
        """\
        <?xml version="1.0" ?>
        <user>
          <name>Alpha</name>
          <login>Bravo</login>
        </user>"""
        factory = XmlFactory("user")
        factory["name"] = "Alpha"
        factory["login"] = "Bravo"

        assert factory.GetContents(xml_header=True) == dedent(self.testSimplest.__doc__)
        assert factory.AsDict() == {"login": "Bravo", "name": "Alpha"}
        assert factory.AsJson() == '{"name": "Alpha", "login": "Bravo"}'

    def testSimple(self):
        """\
        <user>
          <name>Alpha</name>
          <login>Bravo</login>
          <location>
            <city>Charlie</city>
          </location>
        </user>"""
        factory = XmlFactory("user")
        factory["name"] = "Alpha"
        factory["login"] = "Bravo"
        factory["location/city"] = "Charlie"

        assert factory.GetContents() == dedent(self.testSimple.__doc__)
        assert factory.AsDict() == {
            "login": "Bravo",
            "name": "Alpha",
            "location": {"city": "Charlie"},
        }
        assert (
            factory.AsJson()
            == '{"name": "Alpha", "login": "Bravo", "location": {"city": "Charlie"}}'
        )

    def testAttributes(self):
        """\
        <root>
          <alpha one="1" two="2">Alpha</alpha>
          <bravo>
            <charlie three="3"/>
          </bravo>
        </root>"""
        factory = XmlFactory("root")
        factory["alpha"] = "Alpha"
        factory["alpha@one"] = "1"
        factory["alpha@two"] = "2"
        factory["bravo/charlie@three"] = "3"

        assert factory.GetContents() == dedent(self.testAttributes.__doc__)
        # We're ignoring attributes and empty tags for now.
        assert factory.AsDict() == {"alpha": "Alpha", "bravo": {"charlie": None}}
        assert factory.AsJson() == '{"alpha": "Alpha", "bravo": {"charlie": null}}'

    def testRepeatingTags(self):
        """\
        <root>
          <elements>
            <name>Alpha</name>
            <name>Bravo</name>
            <name>Charlie</name>
          </elements>
          <components>
            <component>
              <name>Alpha</name>
            </component>
            <component>
              <name>Bravo</name>
            </component>
            <component>
              <name>Charlie</name>
            </component>
          </components>
        </root>"""
        factory = XmlFactory("root")
        factory["elements/name"] = "Alpha"
        factory["elements/name+"] = "Bravo"
        factory["elements/name+"] = "Charlie"

        factory["components/component+/name"] = "Alpha"
        factory["components/component+/name"] = "Bravo"
        factory["components/component+/name"] = "Charlie"

        assert factory.GetContents() == dedent(self.testRepeatingTags.__doc__)
        assert factory.AsDict() == {
            "elements": {"name": ["Alpha", "Bravo", "Charlie"]},
            "components": {
                "component": [{"name": "Alpha"}, {"name": "Bravo"}, {"name": "Charlie"}]
            },
        }
        assert (
            factory.AsJson()
            == '{"elements": {"name": ["Alpha", "Bravo", "Charlie"]}, "components": {"component": [{"name": "Alpha"}, {"name": "Bravo"}, {"name": "Charlie"}]}}'
        )

    def testHudsonJob(self):
        """\
        <project>
          <actions/>
          <description/>
          <logRotator>
            <daysToKeep>7</daysToKeep>
            <numToKeep>7</numToKeep>
          </logRotator>
          <keepDependencies>false</keepDependencies>
          <properties/>
          <scm class="hudson.scm.SubversionSCM">
            <useUpdate>true</useUpdate>
            <excludedRegions/>
            <excludedUsers/>
            <excludedRevprop/>
          </scm>
          <assignedNode>KATARN</assignedNode>
          <canRoam>false</canRoam>
          <disabled>false</disabled>
          <blockBuildWhenUpstreamBuilding>true</blockBuildWhenUpstreamBuilding>
          <concurrentBuild>false</concurrentBuild>
          <buildWrappers/>
          <customWorkspace>WORKSPACE</customWorkspace>
        </project>"""
        factory = XmlFactory("project")
        factory["actions"]
        factory["description"]
        factory["logRotator/daysToKeep"] = "7"
        factory["logRotator/numToKeep"] = "7"
        factory["keepDependencies"] = "false"
        factory["properties"]
        factory["scm@class"] = "hudson.scm.SubversionSCM"
        factory["scm/useUpdate"] = "true"
        factory["scm/excludedRegions"]
        factory["scm/excludedUsers"]
        factory["scm/excludedRevprop"]
        factory["assignedNode"] = "KATARN"
        factory["canRoam"] = "false"
        factory["disabled"] = "false"
        factory["blockBuildWhenUpstreamBuilding"] = "true"
        factory["concurrentBuild"] = "false"
        factory["buildWrappers"]
        factory["customWorkspace"] = "WORKSPACE"

        assert factory.GetContents() == dedent(self.testHudsonJob.__doc__)

    def testTriggerClass(self):
        """\
        <root>
          <triggers class="vector"/>
        </root>"""
        # Simulating the use for HudsonJobGenerator._CreateTriggers
        factory = XmlFactory("root")
        triggers = factory["triggers"]
        triggers["@class"] = "vector"

        assert factory.GetContents() == dedent(self.testTriggerClass.__doc__)

    def testTypeError(self):
        with pytest.raises(TypeError):
            XmlFactory(9)

    def testPrettyXMLToStream(self, input_xml):
        """\
        <root>
          <alpha enabled="true">
            <bravo>
              <charlie/>
            </bravo>
            <bravo.one/>
            <delta>XXX</delta>
          </alpha>
        </root>"""
        iss = StringIO(input_xml)
        oss = StringIO()

        WritePrettyXML(iss, oss)
        assert oss.getvalue() == dedent(self.testPrettyXMLToStream.__doc__)

    def testPrettyXMLToFile(self, input_xml, tmpdir):
        iss = StringIO(input_xml)
        obtained_filename = tmpdir / "pretty.obtained.xml"

        with open(str(obtained_filename), "w") as f:
            WritePrettyXML(iss, f)
        assert obtained_filename.read() == dedent(
            """\
            <root>
              <alpha enabled="true">
                <bravo>
                  <charlie/>
                </bravo>
                <bravo.one/>
                <delta>XXX</delta>
              </alpha>
            </root>"""
        )

    def testEscape(self):
        element = ElementTree.Element("root")
        element.attrib["name"] = "<no>"
        element.text = "> 3"
        oss = StringIO()
        WritePrettyXMLElement(oss, element)
        assert oss.getvalue() == '<root name="&lt;no&gt;">&gt; 3</root>'

        element = ElementTree.fromstring(oss.getvalue())
        assert element.attrib["name"] == "<no>"
        assert element.text == "> 3"


@pytest.fixture
def input_xml():
    return (
        '<root><alpha enabled="true"><bravo><charlie/></bravo><bravo.one/>'
        "<delta>XXX</delta></alpha></root>"
    )
