# cite-runner

Simplify testing your OGC implementation server against [CITE](https://github.com/opengeospatial/cite/wiki). This
repository contains a CITE runner that can be called as a github action. It can also be used standalone, which allows
integration with other CI platforms or running locally.

This code can either:

- Spin up a docker container with the [OGC TeamEngine image](https://hub.docker.com/r/ogccite/teamengine-production),
  running test suites in an isolated CI environment
- Use an existing TeamEngine deployment


## Running as a GitHub action

### Inputs

This action expects the following inputs to be provided:

- `test_suite_identifier` - Identifier of the test suite to be executed. Test suite identifiers can be gotten from the
  documentation at <http://cite.opengeospatial.org/teamengine/>. Example:

  ```yaml
  test_suite_identifier: 'ogcapi-features-1.0'
  ```

- `test_session_arguments` - Test session arguments to be passed to TeamEngine. These depend on the test suite that is
  going to be executed. Must be provided as a space-separated list of `key=value` pairs. Examples:

  - A simple yaml string
    ```yaml
    test_session_arguments: 'iut=http://localhost:5001 noofcollections=-1'
    ```

  - If you prefer to use a multiline string, then  we recommend use of YAML *folded blocks* with the _strip_
    chomping indicator (AKA put a dash after the folded block indicator, AKA this: `>-`)
    ```yaml
    test_session_arguments: >-
      iut=http://localhost:5001
      noofcollections=-1
    ```

- `teamengine_url` - **OPTIONAL** - URL of the TeamEngine instance to be used for running tests. If this parameter
  is not specified then the action will spin up a local TeamEngine docker container and use it for testing. If you
  specify a custom TeamEngine URL this action will also try to find authentication-related environment variables and
  use them. These environment variables must be named `teamengine_username` and `teamengine_password`

  Note that the value of this parameter must be the URL of the landing page of the TeamEngine service, which usually is
  located at the `/teamengine` path. Examples:

  - When spinning up a local docker instance there is no need to supply this argument

  - When using the remote TeamEngine instance located at `https://my-server` with a pre-existing user `myself` and
    a password of `something`:

    ```yaml
    teamengine_url: 'https://my-server/teamengine'
    teamengine_username: 'myself'
    teamengine_password: 'something'
    ```

- `teamengine_username` - **OPTIONAL** - Username to be used when logging in to a remote TeamEngine instance.
  Defaults to `ogctest`, which is a user that is pre-created on the official TeamEngine docker image.

- `teamengine_password` - **OPTIONAL** - Password to be used when logging in to a remote TeamEngine instance.
  Defaults to `ogctest`, which is the password used for the pre-created user on the official TeamEngine docker image

- `treat_skipped_tests_as_failures` - **OPTIONAL** - Whether the presence of skipped tests should be interpreted as
  an overall failure of the test suite or not. Defaults to `false`

- `network_timeout_seconds` - **OPTIONAL** - Timeout value for network requests. Defaults to `120`

### Usage

The below examples define a GitHub workflow for testing pygeoapi.

Simple usage, running the `ogcapi-features-1.0` test suite whenever there is a `push`:

```yaml
on:
  push:

jobs:

  perform-cite-testing:
    runs-on: ubuntu-22.04
    steps:
      - name: grab code
        uses: actions/checkout@v4

      - name: start pygeoapi with suitable CITE data and config
        run: >
          docker compose -f tests/cite/compose.test-cite.yaml up --detach

      - name: wait for pygeoapi to be usable
        uses: raschmitt/wait-for-healthy-container@v1.0.1
        with:
          container-name: pygeoapi-cite-pygeoapi-1
          timeout: 120

      - name: test ogcapi-features compliancy
        uses: OSGEO/cite-runner@main
        with:
          test_suite_identifier: 'ogcapi-features-1.0'
          test_session_arguments: >-
            iut=http://localhost:5001
            noofcollections=-1
```

A slightly more complex example, using a matrix to test both `ogcapi-features-1.0`
and `ogcapi-processes-1.0` test suites in parallel:

```yaml
on:
  push:

env:
  COLUMNS: 120


jobs:

  perform-cite-testing:
    strategy:
      matrix:
        test-suite:
          - suite-id: ogcapi-features-1.0
            arguments: >-
              iut=http://localhost:5001
              noofcollections=-1
          - suite-id: ogcapi-processes-1.0
            arguments: >-
              iut=http://localhost:5001
              noofcollections=-1

    runs-on: ubuntu-22.04
    steps:

      - name: grab code
        uses: actions/checkout@v4

      - name: start pygeoapi with suitable CITE data and config
        run: >
          docker compose -f tests/cite/compose.test-cite.yaml up --detach

      - name: wait for pygeoapi to be usable
        uses: raschmitt/wait-for-healthy-container@v1.0.1
        with:
          container-name: pygeoapi-cite-pygeoapi-1
          timeout: 120

      - name: collect docker logs on failure
        if: failure()
        uses: jwalton/gh-docker-logs@v2.2.2
        with:
          images: ghcr.io/geopython/pygeoapi
          tail: 500

      - name: test ogcapi-features compliancy
        uses: OSGEO/cite-runner@main
        with:
          test_suite_identifier: ${{ matrix.test-suite.suite-id }}
          test_session_arguments: ${{ matrix.test-suite.arguments }}

```


## Running locally or on other CI platforms

This action's code can also be installed locally:

- Install [poetry](https://python-poetry.org/docs/)
- Clone this repository:

  ```shell
  git clone https://github.com/OSGeo/cite-runner.git
  ```
- Install the code:

  ```shell
  cd cite-runner
  poetry install
  ```

- Start your service to be tested. Let's assume it is already running on `http://localhost:5000`

- Run the TeamEngine docker image locally:

  ```shell
  docker run \
    --rm \
    --name teamengine \
    --network=host \
    ogccite/teamengine-production:1.0-SNAPSHOT
  ```

- Run the action code with

  ```shell
  poetry run cite-runner --help
  ```

There are additional commands and options which can be used when running locally, which allow controlling the output
format and how the inputs are supplied. Read the online documentation for more details.


## Test suites which are known to work

<table>
<thead>
<tr>
<th>test suite identifier</th>
<th>arguments</th>
</tr>
</thead>
<tbody>
<tr>
    <td>ogcapi-features-1.0</td>
    <td>
      <ul>
        <li>iut</li>
        <li>noofcollections</li>
      </ul>
    </td>
</tr>
<tr>
    <td>ogcapi-processes-1.0</td>
    <td>
      <ul>
        <li>iut</li>
        <li>noofcollections</li>
      </ul>
    </td>
</tr>
<tr>
    <td>ogcapi-edr10</td>
    <td>
      <ul>
        <li>iut</li>
        <li>apiDefinition</li>
      </ul>
    </td>
</tr>
<tr>
    <td>ogcapi-tiles10</td>
    <td>
      <ul>
        <li>iut</li>
        <li>tilematrixsetdefnitionuri</li>
        <li>urltemplatefortiles</li>
        <li>tilematrix</li>
        <li>mintilerow</li>
        <li>maxtilerow</li>
        <li>mintilecol</li>
        <li>maxtilecol</li>
      </ul>
    </td>
</tr>
</tbody>
</table>


## Development

After having clone this repository, install the code with dev dependencies by running:

```shell
poetry install --with dev
```

Enable the pre-commit hooks by running:

```shell
poetry run pre-commit install
```

Optionally, do a first run of pre-commit on all files, which will also initialize
pre-commit's hooks:

```shell
poetry run pre-commit run --all-files
```
