from __future__ import unicode_literals
from aasimar.shared_commands import BuildCommand
from ben10.foundation.decorators import Override



#===================================================================================================
# JobsDone10BuildCommand
#===================================================================================================
class JobsDone10BuildCommand(BuildCommand):

    name = 'JobsDone10BuildCommand'

    @Override(BuildCommand.EvBuild)
    def EvBuild(self, args):
        if not self.opts.sub_build:
            self.BuildDependencies()

        self.Clean()
        self.RunTests(jobs=6, xml=True, verbose=1)
