FROM python:3.14.0-slim-bookworm@sha256:8a8d3341dfc71b7420256ceff425f64247da7e23fbe3fc23c3ea8cfbad59096d

RUN apt-get update && apt-get upgrade -y
RUN apt-get install git -y
COPY --from=ghcr.io/astral-sh/uv:0.9.6@sha256:4b96ee9429583983fd172c33a02ecac5242d63fb46bc27804748e38c1cc9ad0d /uv /uvx /bin/

WORKDIR /ai-langchain-based-discovery

COPY /ai-langchain-based-discovery/pyproject.toml  /ai-langchain-based-discovery/uv.lock  ./
RUN uv sync --locked --no-dev --no-cache
RUN pip install --upgrade pip

COPY /ai-langchain-based-discovery .

ENV AICORE_RESOURCE_GROUP=default
ENV LLM_DEPLOYMENT=gpt-4.1

USER 65534

CMD [ "uv", "run", "--no-sync", "--no-dev", "--no-cache", "main.py" ]
