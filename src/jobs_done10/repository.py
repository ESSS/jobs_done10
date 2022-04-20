import re

import attr


@attr.s(auto_attribs=True, frozen=True)
class Repository(object):
    """
    Represents a source control repository used in a continuous integration job.
    """

    # Repository clone URL.
    url: str
    # Branch used in a particular job.
    branch: str = "master"

    @property
    def name(self):
        """
        Repository name, determined from URL.

        e.g.
            url = 'https://server/repo.git'
            name = 'repo'
        """
        return re.match(r".*/([^\./]+)(\.git/?)?$", self.url).groups()[0]
