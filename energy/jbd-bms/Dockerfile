FROM python:3.10-alpine

RUN apk add --no-cache gcc musl-dev libffi-dev

RUN adduser -D -h /app app
RUN addgroup app dialout
USER app

COPY pyproject.toml /app
COPY poetry.lock /app

WORKDIR /app
ENV PATH=${PATH}:/app/.local/bin

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

COPY run.py /app
COPY config.yml /app
COPY jbd /app

ENTRYPOINT ["python", "run.py"]