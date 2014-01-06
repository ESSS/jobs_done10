from sharedscripts10.namespace.namespace_types import PATHLIST
from sharedscripts10.shared_scripts.esss_project import EsssProject



#===================================================================================================
# JobsDone10
#===================================================================================================
class JobsDone10(EsssProject):

    NAME = 'jobs_done10'

    DEPENDENCIES = [
        'git',  # Used when creating jobs from local repository
        'python_jenkins',
        'pyyaml',

        'ben10',
    ]


    NAMESPACE_VARIABLES = {
        '$PATH' : PATHLIST('`self.scripts_dir`'),

        '>jd_eden' : 'jobs_done jenkins http://eden.fln.esss.com.br:9090/ --username=dev --password=***REMOVED***',
        '>jd_yoda' : 'jobs_done jenkins http://hub.esss.com.br:9090/ --username=dev --password=***REMOVED***',
    }
