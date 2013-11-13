from sharedscripts10.shared_scripts.esss_application import EsssTool
from sharedscripts10.namespace.namespace_types import PATHLIST



#===================================================================================================
# JobsDone10
#===================================================================================================
class JobsDone10(EsssTool):

    NAME = 'jobs_done10'

    DEPENDENCIES = [
        'ben10',
        'sharedscripts10',
        'jenkins_job_builder',
        'python_jenkins',
    ]


    NAMESPACE_VARIABLES = {
        '$PATH' : PATHLIST('`self.scripts_dir`')
    }
