from ben10.foundation.bunch import Bunch



#===================================================================================================
#  Repository
#===================================================================================================
class Repository(Bunch):
    '''
    Represents a source control repository used in a continuous integration job.

    :cvar str url:

    :cvar str branch:
        Branch used in a particular job

    :cvar str name:
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
