from jobs_done10.repository import Repository
from jobs_done10.jobs_done_file import JobsDoneFile
from ben10.interface import ImplementsInterface
from jobs_done10.job_builder import IJobBuilder, JobBuilderConfigurator, JobBuilderAttributeError
import pytest
import contextlib



#===================================================================================================
# Test
#===================================================================================================
class Test(object):

    def testJobBuilderConfigurator(self, monkeypatch):
        class MyBuilder():
            ImplementsInterface(IJobBuilder)

            def SetRepository(self, repository):
                assert repository.url == 'http://repo.git'

            def SetVariation(self, variation):
                assert variation == {'id':1}

            def SetBuildBatchCommand(self, command):
                assert command == 'command'

            def Build(self):
                pass

            def Reset(self):
                pass

        jobs_done_file = JobsDoneFile()
        jobs_done_file.variation = {'id':1}
        repository = Repository(url='http://repo.git')

        builder = MyBuilder()

        # Test basic calls
        with ExpectedCalls(builder, Reset=1, SetRepository=1, SetVariation=1, SetBuildBatchCommand=0):
            JobBuilderConfigurator.Configure(builder, jobs_done_file, repository)

        # Set some more values to jobs_done_file, and make sure it is called
        jobs_done_file.build_batch_command = 'command'
        with ExpectedCalls(builder, Reset=1, SetRepository=1, SetVariation=1, SetBuildBatchCommand=1):
            JobBuilderConfigurator.Configure(builder, jobs_done_file, repository)

        # Try calling a missing option
        jobs_done_file.boosttest_patterns = 'patterns'
        with pytest.raises(JobBuilderAttributeError):
            JobBuilderConfigurator.Configure(builder, jobs_done_file, repository)



#===================================================================================================
# ExpectedCalls
#===================================================================================================
@contextlib.contextmanager
def ExpectedCalls(obj, **function_expected_calls):
    calls = {}

    def _GetWrapper(hash_, original_function):
        import functools
        @functools.wraps(original_function)
        def Wrapped(*args, **kwargs):
            calls[hash_][0] += 1
            original_function(*args, **kwargs)
        return Wrapped

    # __enter__
    for function_name, expected_calls in function_expected_calls.iteritems():
        hash_ = (obj, function_name)

        original_function = getattr(obj, function_name)

        # Register expected calls
        calls[hash_] = [0, expected_calls, original_function]

        # Wrap function to start counting calls
        setattr(obj, function_name, _GetWrapper(hash_, original_function))

    yield

    # __exit__
    try:
        for (_, function_name), (obtained, expected, _) in calls.items():
            assert obtained == expected, \
                'Expected "%d" calls for function "%s", but got "%d"' % \
                (expected, function_name, obtained)
    finally:
        # Clear all mocks
        for (obj, function_name), (_, _, original_function) in calls.items():
            setattr(obj, function_name, original_function)
