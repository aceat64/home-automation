FROM python:3.10-alpine

RUN apk add --no-cache gcc musl-dev libffi-dev

RUN mkdir /app

COPY pyproject.toml /app
COPY poetry.lock /app
COPY run.py /app
COPY config.yml /app

WORKDIR /app
ENV PYTHONPATH=${PYTHONPATH}:${PWD}

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

ENTRYPOINT ["python", "run.py"]