FROM python:3.6.5

COPY ./.env /jobsdone/.env
COPY ./source/python /jobsdone/source/python
COPY ./setup.py /jobsdone/setup.py

WORKDIR /jobsdone

RUN pip install . gunicorn

ENV JOBSDONE_DOTENV /jobsdone/.env

EXPOSE 5000

CMD ["gunicorn", "jobs_done10.server:app", "-b", "0.0.0.0:5000", "--workers", "4", "--timeout", "300", "--log-level=debug"]