ARG FUNCTION_DIR="/function"

FROM python:3.10-slim as build-image
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    COLUMNS=200 \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

ARG FUNCTION_DIR

RUN mkdir -p ${FUNCTION_DIR}


RUN pip install poetry
COPY poetry.lock pyproject.toml ./
RUN poetry install --only main

RUN mv .venv/lib/python3.10/site-packages/* ${FUNCTION_DIR}/

RUN pip install \
      --target ${FUNCTION_DIR} \
      awslambdaric

COPY . ${FUNCTION_DIR}

FROM python:3.10-slim

ARG FUNCTION_DIR

WORKDIR ${FUNCTION_DIR}

COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD [ "lambda.handler" ]
