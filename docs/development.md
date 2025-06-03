---
hide:
   - navigation
---

# Development

ogc-cite-runner is implemented in Python.

The standalone application depends on the following third-party projects:

- [typer:material-open-in-new:]{: target="blank_" } for CLI commands
- [pydantic:material-open-in-new:]{: target="blank_" } for models
- [jinja:material-open-in-new:]{: target="blank_" } for output format templates
- [httpx:material-open-in-new:]{: target="blank_" } for making network requests
- [lxml:material-open-in-new:]{: target="blank_" } for parsing teamengine responses
- [mkdocs:material-open-in-new:]{: target="blank_" } for documentation

### Brief implementation overview

ogc-cite-runner runs CITE tests suites by calling [teamengine's web API:material-open-in-new:]{: target="blank_" }. It
requests test suite results in the EARL (AKA the W3C Evaluation and Report
Language) format, which is XML-based.

After obtaining a test suite run result in EARL format, ogc-cite-runner parses it
into an instance of `models.TestSuiteResult`, its internal data structure.From
there, it is able to serialize it into either JSON or markdown.


### Setting up a development environment

In a brief nutshell:

1. Fork the ogc-cite-runner repository

2. Clone your fork to your local environment

3. Install [uv:material-open-in-new:]{: target="blank_" }

4. Use uv to install the ogc-cite-runner code locally. This will create a virtualenv and install all
   dependencies needed for development, including for working on docs:

    ```shell
    uv sync
    ```

5. Optionally (but strongly recommended) enable the [pre-commit:material-open-in-new:]{: target="blank_" } hooks
   provided by ogc-cite-runner:

    ```shell
    uv run pre-commit install
    ```

6. Stand up a docker container with a local teamengine instance:

    ```shell
    docker run \
        --rm \
        --name=teamengine \
        --add-host=host.docker.internal:host-gateway \
        --publish=9080:8080 \
        ogccite/teamengine-production:1.0-SNAPSHOT
    ```

    You should now be able to use `http:localhost:9080/teamengine` as the teamengine URL in
    ogc-cite-runner.

    !!! note

        Using docker's `--add-host=host.docker.internal:host-gateway` is necessary when running
        docker engine, as discussed in the [docker engine docs:material-open-in-new:]{: target="blank_" }. If
        you are using docker desktop on Windows or macOS you can omit this flag.

7.  You can run ogc-cite-runner via uv with:

    ```shell
    uv run ogc-cite-runner
    ```

    !!! warning

         When using ogc-cite-runner with a local teamengine instance that is running via docker and also testing an
         OGC service that is running locally on the same machine, you must not use `localhost` when providing the
         service's URL to teamengine, but rather use `host.docker.internal`.

         As an example:

         ```shell
         uv run ogc-cite-runner execute-test-suite \
             http://localhost:9081/teamengine \
             ogcapi-features-1.0 \
             --suite-input iut http://host.docker.internal:9082
         ```


### Running tests

Most tests can be run with:

 ```shell
 uv run pytest
 ```

ogc-cite-runner also includes a workflow for testing itself when running as a GitHub action. This can be run locally
with a tool like [act:material-open-in-new:]{: target="blank_" }.

 ```shell
 act \
     --workflows .github/workflows/test-action.yaml \
     --rm \
     --platform ubuntu-24.04=ghcr.io/catthehacker/ubuntu:act-24.04 \
     --container-options="-p 9092:9092" \
     --artifact-server-path $PWD/.artifacts
 ```

The `.github/workflows/test-action.yaml` workflow launches a simple HTTP server which contains a very incomplete
implementation of OGC API - Features and then uses the ogc-cite-runner GitHub action to run the `ogcapi-features-1.0`
test suite on it. It then captures the ogc-cite-runner output, and runs it through some Python tests to verify the
result matches what is expected.


### Documentation

If you want to work on documentation, you can start the mkdocs server with:

 ```shell
 uv run mkdocs serve
 ```

Now edit files under the `/docs` directory and check whether they match your expected result in the mkdocs dev server,
which would be running at `http://localhost:8000/ogc-cite-runner/


## Release management

ogc-cite-runner releases are managed with a [GitHub actions workflow:material-open-in-new:]{: target="_blank" }, which is
set up to run whenever a new tag named `v*` is pushed to the repository. This workflow will:

- Call the CI workflow, which takes care of testing and building the application
- Create a GitHub release
- Publish the built application to PyPI

!!! note

    The release workflow is not fully automated, requiring the ogc-cite-runner maintainers to explicitly provide
    approval of new runs. This is intentional.



[act:material-open-in-new:]: https://nektosact.com/introduction.html
[docker engine docs:material-open-in-new:]: https://docs.docker.com/reference/cli/docker/container/run/#add-host
[GitHub actions workflow:material-open-in-new:]: https://github.com/OSGeo/ogc-cite-runner/blob/main/.github/workflows/release.yaml
[httpx:material-open-in-new:]: https://www.python-httpx.org/
[jinja:material-open-in-new:]: https://jinja.palletsprojects.com/en/stable/
[lxml:material-open-in-new:]: https://lxml.de/
[mkdocs:material-open-in-new:]: https://www.mkdocs.org/
[pre-commit:material-open-in-new:]: https://pre-commit.com/
[pydantic:material-open-in-new:]: https://docs.pydantic.dev/latest/
[teamengine's web API:material-open-in-new:]: https://opengeospatial.github.io/teamengine/users.html
[typer:material-open-in-new:]: https://typer.tiangolo.com/
[uv:material-open-in-new:]: https://docs.astral.sh/uv/
