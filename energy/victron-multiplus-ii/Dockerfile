ARG PYTHON_VERSION=3.11

#
# Stage: prep
# Load the source files and relevant system dependencies
#
FROM python:${PYTHON_VERSION} as prep

ENV \
  # Don't create .pyc files, these aren't useful in a container imager
  PYTHONDONTWRITEBYTECODE=1 \
  # Immediately write to stdout and stderr instead of buffering the output
  PYTHONUNBUFFERED=1 \
  # Dump tracebacks when non-python code crashes, useful for diagnosing issues
  PYTHONFAULTHANDLER=1

# Setup a venv and install Poetry
# Ref: https://python-poetry.org/docs/#ci-recommendations
ARG POETRY_VERSION=1.6.1
ENV PATH="/opt/poetry/bin:${PATH}"
RUN python3 -m venv /opt/poetry && \
  pip install --no-cache-dir poetry==${POETRY_VERSION} && \
  poetry --version

WORKDIR /app

# Configure Poetry to install the project in /app/.venv
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

# Copy in just the files needed for installing dependencies
COPY pyproject.toml poetry.lock ./
# Install just the main dependencies (no dev)
RUN poetry install --no-root --only main

# Now copy over the rest of our project. This is done separately from installing
# dependencies, so that changes to the project files won't invalidate the cache.
# NOTE: Any files/folders that would bloat the image should be listed in .dockerignore
COPY . .

# install the project
RUN poetry install --only main


#
# Stage: production
# Slim/minimal final image.
#
FROM python:${PYTHON_VERSION} as production

ENV \
  # Don't create .pyc files, these aren't useful in a container imager
  PYTHONDONTWRITEBYTECODE=1 \
  # Immediately write to stdout and stderr instead of buffering the output
  PYTHONUNBUFFERED=1 \
  # Dump tracebacks when non-python code crashes, useful for diagnosing issues
  PYTHONFAULTHANDLER=1

WORKDIR /app

# Copy our files over from the prep stage
COPY --from=prep /app .

# Create the app user and group
RUN groupadd --gid 1000 app && \
  useradd --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin --uid 1000 --gid 1000 --groups dialout app
# Switch to app user
USER app

# Add the app venv to $PATH
ENV PATH="/app/.venv/bin:${PATH}"

# The command that will be run:
ENTRYPOINT ["python", "run.py"]