# FROM ghcr-io.docker.kubit.dev/astral-sh/uv:python3.13-bookworm-slim AS fast-uv
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS fast-uv

WORKDIR /app

COPY pyproject.toml pyproject.toml

# RUN uv pip install --index-url https://pypi.kubit.dev/simple/  --system --no-cache-dir .
RUN uv pip install --system --no-cache-dir .


FROM python:3.13-slim AS fast-server

RUN rm -rf /usr/local/lib/python3.13/site-packages
COPY --from=fast-uv /usr/local/lib/python3.13/site-packages \
                    /usr/local/lib/python3.13/site-packages

WORKDIR /app

RUN addgroup --system --gid 1000 user \
    && adduser --system --uid 1000 --ingroup user --disabled-password --gecos '' --home /home/user user \
    && mkdir -p /app/logs \
    && chown -R user:user /app/logs

USER user
COPY --chown=user:user . .

CMD [ "python", "main.py" ]
