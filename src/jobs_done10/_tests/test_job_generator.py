import contextlib

import pytest

from jobs_done10.job_generator import JobGeneratorAttributeError
from jobs_done10.job_generator import JobGeneratorConfigurator
from jobs_done10.jobs_done_job import JobsDoneJob
from jobs_done10.repository import Repository


def testJobGeneratorConfigurator():
    class MyGenerator(object):
        def SetRepository(self, repository):
            assert repository.url == "http://repo.git"

        def SetMatrix(self, matrix, matrix_row):
            assert matrix == {"id": [1, 2, 3]}
            assert matrix_row == {"id": 1}

        def SetBuildBatchCommands(self, commands):
            assert commands == ["command"]

        def Reset(self):
            pass

    jobs_done_job = JobsDoneJob()
    jobs_done_job.matrix = {"id": [1, 2, 3]}
    jobs_done_job.matrix_row = {"id": 1}
    jobs_done_job.repository = Repository(url="http://repo.git")

    generator = MyGenerator()

    # Test basic calls
    with ExpectedCalls(
        generator, Reset=1, SetRepository=1, SetMatrix=1, SetBuildBatchCommands=0
    ):
        JobGeneratorConfigurator.Configure(generator, jobs_done_job)

    # Set some more values to jobs_done_job, and make sure it is called
    jobs_done_job.build_batch_commands = ["command"]
    with ExpectedCalls(
        generator, Reset=1, SetRepository=1, SetMatrix=1, SetBuildBatchCommands=1
    ):
        JobGeneratorConfigurator.Configure(generator, jobs_done_job)

    # Try calling a missing option
    jobs_done_job.boosttest_patterns = "patterns"
    with pytest.raises(JobGeneratorAttributeError):
        JobGeneratorConfigurator.Configure(generator, jobs_done_job)


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
    for function_name, expected_calls in function_expected_calls.items():
        hash_ = (obj, function_name)

        original_function = getattr(obj, function_name)

        # Register expected calls
        calls[hash_] = [0, expected_calls, original_function]

        # Wrap function to start counting calls
        setattr(obj, function_name, _GetWrapper(hash_, original_function))

    yield

    # __exit__
    try:
        for (_, function_name), (obtained, expected, _) in list(calls.items()):
            assert (
                obtained == expected
            ), 'Expected "%d" calls for function "%s", but got "%d"' % (
                expected,
                function_name,
                obtained,
            )
    finally:
        # Clear all mocks
        for (obj, function_name), (_, _, original_function) in list(calls.items()):
            setattr(obj, function_name, original_function)
