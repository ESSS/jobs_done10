from ben10.clikit.app import App


# Create command line application
jobs_done_application = App('jobs_done')

# Configure application with available builders
from jobs_done10.builders.jenkins import ConfigureCommandLineInterface
ConfigureCommandLineInterface(jobs_done_application)

# Run application
if __name__ == '__main__':
    jobs_done_application.Main()
