ARG BASE=python:3.12.10-slim-bullseye

# Temp stage: artifact build (requires compilers that we exclude from final worker image)
FROM ${BASE} AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev

COPY requirements/ requirements/
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements/worker.txt



### Final docker image
FROM ${BASE}

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy all application source code and tests into the image
COPY . .

# quick hack; fiddle with importing this_compute as module later
ENV PYTHONPATH="."
# TODO: Add final user permissions, etc, to lock down image
