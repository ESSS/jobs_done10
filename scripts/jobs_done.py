from __future__ import unicode_literals
from clikit.app import App
from jobs_done10.generators.jenkins import ConfigureCommandLineInterface


# Create command line application
jobs_done_application = App('jobs_done')

# Configure application with available generators
ConfigureCommandLineInterface(jobs_done_application)


# Run application
main = jobs_done_application.Main
if __name__ == '__main__':
    main()
