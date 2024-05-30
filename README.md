
**Table of Contents:**

- [Development Dependencies](#development-dependencies)
- [Local testing](#local-testing)

# Development

In order to develop for this project you need the following tools installed:

1. [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. [pre-commit](https://pre-commit.com/#install)


**Make sure you run `pre-commit install` once after cloning to initialize the git commit hooks**

# Local testing

## Using Poetry

1. Make sure that you have python and poetry installed. ([Poetry installation instructions](https://python-poetry.org/docs/#installation)) ([pyenv](https://github.com/pyenv/pyenv) or [pyenv-win](https://github.com/pyenv-win/pyenv-win) is the recommended python version manager.)
2. Clone the repo to your machine and open a terminal on the project root.
3. Run `poetry env use python 3.11.9` and then `poetry install`.
4. Run `poetry run pre-commit install`
5. Optional: Set the environment as the default for the project in your IDE for debugging and testing.
6. You should be good to go. Add any missing libraries using `poetry add`.
7. Use `poetry export --only main -o requirements.txt --without-hashes --without-urls` to update the `requirements.txt` file. (requirements.txt is needed for deployment to DE, because DE doesn't support poetry yet. pyproject.toml is used for local development and project management.)
