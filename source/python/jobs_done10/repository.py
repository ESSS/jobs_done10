from __future__ import unicode_literals
from ben10.foundation.bunch import Bunch



#===================================================================================================
#  Repository
#===================================================================================================
class Repository(Bunch):
    '''
    Represents a source control repository used in a continuous integration job.

    :cvar unicode url:
        Repository clone URL

    :cvar unicode branch:
        Branch used in a particular job

    :cvar unicode name:
        Repository name, determined from URL.

        e.g.
            url = 'https://server/repo.git'
            name = 'repo'
    '''
    url = None
    branch = 'master'

    @property
    def name(self):
        import re
        return re.match('.*/([^\./]+)(\.git/?)?$', self.url).groups()[0]
