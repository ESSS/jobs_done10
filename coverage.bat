set COVERAGE_MODULE=jobs_done10.log
set COVERAGE_PATH=source\python\jobs_done10\_tests\pytest_log.py
set COVERAGE_MODULE=jobs_done10
set COVERAGE_PATH=source\python\jobs_done10
pytest -n8 --cov-report term-missing --cov %COVERAGE_MODULE% %COVERAGE_PATH%

