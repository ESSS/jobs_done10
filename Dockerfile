FROM python:3.10.5-slim

# We need git for the tests.
ADD ./source.list /etc/apt/source.list
RUN apt-get update &&\
    apt-get install --yes git

# pass with --build-arg SETUPTOOLS_SCM_PRETEND_VERSION=VERSION; this is needed by setuptools_scm
ARG SETUPTOOLS_SCM_PRETEND_VERSION=dev

COPY ./requirements.txt /jobsdone/requirements.txt

WORKDIR /jobsdone

COPY ./README.md /jobsdone/README.md
COPY ./setup.py /jobsdone/setup.py
COPY ./src /jobsdone/src
COPY ./tests /jobsdone/tests

RUN pip install -r requirements.txt .

ENV JOBSDONE_DOTENV /jobsdone/.env

EXPOSE 5000

CMD ["gunicorn", "jobs_done10.server.app:app", "-b", "0.0.0.0:5000", "--workers", "4", "--timeout", "300"]
