from clikit.app import App
from jobs_done10.generators.jenkins import ConfigureCommandLineInterface


# Create command line application
jobs_done_application = App('jobs_done')

# Configure application with available builders
ConfigureCommandLineInterface(jobs_done_application)

# Run application
if __name__ == '__main__':
    jobs_done_application.Main()
