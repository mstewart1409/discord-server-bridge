################################
## B U I L D
################################
FROM python:3.11.9

# Install tools and set timezone to Europe/London
WORKDIR /
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    unzip \
    apt-utils \
    libaio-dev \
    tzdata && \
    echo "Europe/London" > /etc/timezone && \
    ln -snf /usr/share/zoneinfo/Europe/Berlin /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Environment Variables

ENV PATH=/home/user/.local/bin:$PATH
# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1
# Install and build Python dependencies.
ENV POETRY_VERSION=1.8.3


RUN pip install "poetry==$POETRY_VERSION"

WORKDIR /app

# Change user
RUN useradd -m -r user && \
    chown user /app

COPY ./poetry.lock ./pyproject.toml /app/

RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi

COPY . /app/

USER user

# Run app
CMD ["python", "main.py"]
