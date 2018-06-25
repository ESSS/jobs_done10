


#===================================================================================================
#  Repository
#===================================================================================================
class Repository(object):
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

    def __init__(self, url=None, branch='master'):
        self.url = url
        self.branch = branch

    @property
    def name(self):
        import re
        return re.match('.*/([^\./]+)(\.git/?)?$', self.url).groups()[0]


    def __eq__(self, other):
        return self.url == other.url and self.branch == other.branch


    def __ne__(self, other):
        return not self == other
