FROM python:3.6.10-slim

ADD ./source.list /etc/apt/source.list

RUN apt-get update &&\
    apt-get install --yes git

# pass with --build-arg SETUPTOOLS_SCM_PRETEND_VERSION=VERSION; this is needed by setuptools_scm
ARG SETUPTOOLS_SCM_PRETEND_VERSION=dev

COPY ./requirements.txt /jobsdone/requirements.txt

WORKDIR /jobsdone

RUN pip install pip==20.1.1
RUN pip install -r requirements.txt

COPY ./README.md /jobsdone/README.md
COPY ./setup.py /jobsdone/setup.py
COPY ./.env /jobsdone/.env
COPY ./src /jobsdone/src

RUN pip install .

ENV JOBSDONE_DOTENV /jobsdone/.env

EXPOSE 5000

CMD ["gunicorn", "jobs_done10.server.app:app", "-b", "0.0.0.0:5000", "--workers", "4", "--timeout", "300"]
