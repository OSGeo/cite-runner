---
hide:
  - navigation
---

# Running as a GitHub action

![github-action-runner](assets/github-action-demo.png)

## Overview

In order to run ogc-cite-runner as a [GitHub action:material-open-in-new:]{: target="blank_" }, include it in your workflow
and specify which test suite to run, alongside any relevant parameters.


!!! tip

    Although ogc-cite-runner is not yet published in the [GitHub marketplace:material-open-in-new:]{: target="blank_" } it
    can still be used in GitHub CI workflows.

Include it as any other GitHub action, by creating a workflow step that
specifies `uses: OSGEO/ogc-cite-runner` and provide execution parameters in the
`with` parameter.

Here is a simple example usage:

```yaml
jobs:
  perform-cite-testing:
    runs-on: ubuntu-24.04
    steps:

      # other steps which start your OGC implementation and wait for it to become available

      - name: test ogcapi-features compliancy
        uses: OSGEO/ogc-cite-runner@v0.2.0
        with:
          test_suite_identifier: ogcapi-features-1.0
          test_session_arguments: iut=http://localhost:5001
```

## Inputs

When run as a GitHub action, ogc-cite-runner expects the following inputs to be provided:


### `test_suite_identfier`

- **Required**: Yes
- **Description**: Identifier of the test suite to be executed. Test suite identifiers can be gotten from
  the [OGC Test suites section](ogc-test-suites.md).

    Example:

    ```yaml
    test_suite_identifier: 'ogcapi-features-1.0'
    ```


### `test_session_arguments`

- **Required**: Yes
- **Description**: Test session arguments to be passed to TeamEngine. These depend on the test
    suite that is going to be executed.

    Must be provided as a space-separated list of `key=value` pairs. Examples:

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


### `teamengine_url`

- **Required**: No (defaults to not set)
- **Description**: URL of the TeamEngine instance to be used for running tests.

    If this parameter is not specified then the action will spin up a local
    TeamEngine docker container and use it for testing.

    When providing a value for this option, it can be used in conjunction with
    the `teamengine_username` and `teamengine_password` in order to provide
    authentication credentials.

    !!! note
        The value of `teamengine_url` must be the URL of the landing page of
        the TeamEngine service, which usually is located at the `/teamengine` path.

    Examples:

    - When you intend for the action to spin up a local docker instance there is
      no need to supply this argument. The action will run totally self-contained

    - When using the remote TeamEngine instance located at `https://my-server`
      with a pre-existing user `myself` and a password of `something`:

      ```yaml
      teamengine_url: 'https://my-server/teamengine'
      teamengine_username: 'myself'
      teamengine_password: 'something'
      ```


### `teamengine_username`

- **Required**: No (defaults to `ogctest`)
- **Description**: Username to be used when logging in to a remote TeamEngine instance.
  Defaults to `ogctest`, which is a user that is pre-created on the official TeamEngine docker image.


### `teamengine_password`

- **Required**: No (defaults to `ogctest`)
- **Description**: Password to be used when logging in to a remote TeamEngine instance.
  Defaults to `ogctest`, which is the password used for the pre-created user on the official TeamEngine docker image


### `network_timeout_seconds`

- **Required**: No (defaults to `120`)
- **Description**: Timeout value for network requests, in seconds


### `with_failed`

- **Required**: No (defaults to `'false'`)
- **Description**: Whether the output report should include information about failed tests.

    Note that regardless of this input's value, the workflow execution logs always include the full test suite
    execution details, which include any information related to failed tests.

!!! note

    [GitHub actions inputs:material-open-in-new:]{: target="blank_" } are always interpreted as strings by default.
    However, this input is parsed into a boolean with the GitHub actions
    [fromJSON() function:material-open-in-new:]{: target="blank_" } and is then evaluated with
    GitHub's [ternary operator:material-open-in-new:]{: target="blank_" }. This means that if you pass it a value of
    either `'true'` or `'false'` everything will work as intended.



### `with_skipped`

- **Required**: No (defaults to `false`)
- **Description**: Whether the output report should include information about skipped tests

    Note that regardless of this input's value, the workflow execution logs always include the full test suite
    execution details, which include any information related to skipped tests.

!!! note

    [GitHub actions inputs:material-open-in-new:]{: target="blank_" } are always interpreted as strings by default.
    However, this input is parsed into a boolean with the GitHub actions
    [fromJSON() function:material-open-in-new:]{: target="blank_" } and is then evaluated with
    GitHub's [ternary operator:material-open-in-new:]{: target="blank_" }. This means that if you pass it a value of
    either `'true'` or `'false'` everything will work as intended.



### `with_passed`

- **Required**: No (defaults to `false`)
- **Description**: Whether the output report should include information about passed tests

    Note that regardless of this input's value, the workflow execution logs always include the full test suite
    execution details, which include any information related to passed tests.

!!! note

    [GitHub actions inputs:material-open-in-new:]{: target="blank_" } are always interpreted as strings by default.
    However, this input is parsed into a boolean with the GitHub actions
    [fromJSON() function:material-open-in-new:]{: target="blank_" } and is then evaluated with
    GitHub's [ternary operator:material-open-in-new:]{: target="blank_" }. This means that if you pass it a value of
    either `'true'` or `'false'` everything will work as intended.



### `exit_with_error`

- **Required**: No (defaults to `true`)
- **Description**: Whether the action should exit with an error when a suite is declared as failed.

!!! note

    [GitHub actions inputs:material-open-in-new:]{: target="blank_" } are always interpreted as strings by default.
    However, this input is parsed into a boolean with the GitHub actions
    [fromJSON() function:material-open-in-new:]{: target="blank_" } and is then evaluated with
    GitHub's [ternary operator:material-open-in-new:]{: target="blank_" }. This means that if you pass it a value of
    either `'true'` or `'false'` everything will work as intended.



## Outputs

The ogc-cite-runner GitHub Action will provide a single output, which is a full report of the test suite results:


### json_report

This is a JSON document containing the full parsed test suite execution results. You can use it in further GitHub
workflow steps to verify suite execution. As an example of further processing, you can pipe the result to
[jq:material-open-in-new:]{: target="blank_" }, as seen below:

```yaml
- name: "Verify ogc-cite-runner results"
  run: |
  jq '.passed' <<EOF
  ${{ steps.test_cite_runner_github_action.outputs.json_report }}
  EOF
```

!!! tip

    Handling outputs of a GitHub Action that represent JSON data can be a bit tricky. The previous example showcases
    using a [HERE doc:material-open-in-new:]{: target="blank_" }, which has the benefit of preserving whatever
    double/single quotes may be present in the underlying JSON data. We recommend always using this technique to
    process ogc-cite-runner GitHub Action's output


[ogc-cite-runner's own testing workflow:material-open-in-new:]{: target="blank_" } has an additional example of using
the action's output and passing it to another command for further processing.

## Usage examples


### Simple

Simple usage, running the `ogcapi-features-1.0` test suite whenever there is a `push`:

```yaml
on:
  push:

jobs:

  perform-cite-testing:
    runs-on: ubuntu-22.04
    steps:

      # other steps which start your OGC implementation and wait for it to become available

      - name: test ogcapi-features compliancy
        uses: OSGEO/ogc-cite-runner@v0.2.0
        with:
          test_suite_identifier: 'ogcapi-features-1.0'
          test_session_arguments: iut=http://localhost:5001
```


### Provide multiple test suite inputs

In this example we test for compliance with the `ogcapi-tiles-1.0` test suite and provide multiple input parameters.
In order to keep the GitHub workflow file easily readable, inputs are specified by using the YAML `>-` feature mentioned
above, which allows putting them on individual lines.

```yaml
on:
  push:

jobs:

  perform-cite-testing:
    runs-on: ubuntu-22.04
    steps:

      # other steps which start your OGC implementation and wait for it to become available

      - name: test ogcapi-features compliancy
        uses: OSGEO/ogc-cite-runner@v0.2.0
        with:
          test_suite_identifier: 'ogcapi-tiles-1.0'
          test_session_arguments: >-
            iut=http://localhost:5001
            tilematrixsetdefinitionuri=http://www.opengis.net/def/tilematrixset/OGC/1.0/WebMercatorQuad
            urltemplatefortiles=http://localhost:5001/collections/lakes/tiles/WebMercatorQuad/{tileMatrix}/{tileRow}/{tileCol}?f=mvt
            tilematrix=0
            mintilerow=0
            maxtilerow=1
            mintilecol=0
            maxtilecol=1
```


### Customize report and exit status

In this example we ask for inclusion of details on both failed and skipped tests in the generated Markdown report. We
also tell ogc-cite-runner to not exit with an error in case the tests fail. This can be used for cases where you don't
want CITE failures to be breaking your CI workflow.


```yaml
on:
  push:

jobs:

  perform-cite-testing:
    runs-on: ubuntu-22.04
    steps:

      # other steps which start your OGC implementation and wait for it to become available

      - name: test ogcapi-features compliancy
        uses: OSGEO/ogc-cite-runner@v0.2.0
        with:
          test_suite_identifier: 'ogcapi-features-1.0'
          test_session_arguments: iut=http://localhost:5001
          with_failed: "true"
          with_skipped: "true"
          exit_with_error: "false"
```


### Test several suites in parallel

A slightly more complex example, using a matrix to test both `ogcapi-features-1.0`
and `ogcapi-processes-1.0` test suites in parallel:

```yaml
on:
  push:

jobs:

  perform-cite-testing:
    continue-on-error: true
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

      # other steps which start your OGC implementation and wait for it to become available

      - name: test ogcapi-features compliancy
        uses: OSGEO/ogc-cite-runner@v0.2.0
        with:
          test_suite_identifier: ${{ matrix.test-suite.suite-id }}
          test_session_arguments: ${{ matrix.test-suite.arguments }}

```


## Results

The ogc-cite-runner GitHub action stores both:

- Raw suite results, as output directly by OGC TeamEngine. This is an XML file that uses a schema based on the
  W3C EARL format
- Parsed suite results, in Markdown format.

These results are saved as [workflow artifacts:material-open-in-new:]{: target="blank_" } and are available for
download for further processing.

Additionally, ogc-cite-runner also adds the contents of the parsed Markdown file as the job summary, making them directly
visible in the GitHub workflow run overview page:

![github-workflow-job-sumary](assets/github-action-summary.png)

Furthermore, the full suite execution results are also shown in the job logs:

![github-workflow-log](assets/github-action-log-output.png)

!!! note

    The parsed results which are persisted as a Markdown artifact and shown in the job summary respect
    the action parameters:

    - `include_failed_test_details`
    - `include_skipped_test_details`
    - `include_passed_test_details`

    However, the results shown on the job logs always include the full results.

[workflow artifacts:material-open-in-new:]: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/storing-and-sharing-data-from-a-workflow#about-workflow-artifacts


## Implementation details

!!! note

    The information below is ony relevant if you wish to learn about the internals of the ogc-cite-runner GitHub action.

The GitHub action is implemented as a [composite action:material-open-in-new:]{: target="blank_" } in which the most
relevant steps consist of calling ogc-cite-runner as a standalone CLI application. Brief overview of the execution flow:

1. Install uv and set up Python
2. Install ogc-cite-runner
3. If needed, start a TeamEngine docker container
4. Run ogc-cite-runner multiple times

    1. The first execution is where the test suite is actually run. The ogc-cite-runner
       `execute-test-suite-from-github-actions` CLI command is invoked with the `--output-format raw` flag
       and the raw XML result returned by TeamEngine is stored as `raw-result.xml`

    2. The second execution parses the raw result and outputs a full report to the logs. ogc-cite-runner's `parse-result`
       CLI command is invoked with the `--output-format console` flag. Depending on the value of the `exit_with_error`
       action input, the ogc-cite-runner `--exit-with-error/--exit-without-error` flag is set accordingly and the exit code
       of ogc-cite-runner is stored in a variable

        !!! tip

            This step is performed by using a [custom shell:material-open-in-new:]{: target="blank_" } invocation
            which consists of:

            ```yaml
            shell: "bash --noprofile --norc -o pipefail {0}"
            ```

            The only noteworthy change from GitHub's default bash incantation is the omission of the `-e` flag, which
            means [set -e:material-open-in-new:]{: target="blank_" } and has the effect of immediately failing the
            step if one of it's underlying commands exits with a non-zero code.

            The reason why this step does not use `bash -e` is that ogc-cite-runner's GitHub action needs to check the
            exit code of the `ogc-cite-runner parse-result` CLI command (which can be non-zero) and also take into
            account the value of its `exit_with_error` input in order to set the final exit code.

    3. The third execution parses the raw result again and outputs a Markdown report, which is used for the GitHub
       step summary. ogc-cite-runner's `parse-result` CLI command is thus invoked with the `--output-format markdown`
       flag. The contents of the Markdown report are generated in accordance with the values of the
       action's `with_failed`, `with_skipped` and `with_passed` input values.

5. Store both the raw execution result and the generated Markdown report as GitHub job artifacts, making them available
   for download
6. If needed, stop the previously started TeamEngine container
7. Finally, set the action exit code. This is done by retrieving the exit code that had been stored in 4.2 and using it
   to set the overall action exit code.


[ogc-cite-runner's own testing workflow:material-open-in-new:]: https://github.com/OSGeo/ogc-cite-runner/tree/main/.github/workflows/test-action.yaml
[composite action:material-open-in-new:]: https://docs.github.com/en/actions/sharing-automations/creating-actions/creating-a-composite-action
[custom shell:material-open-in-new:]: https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions#jobsjob_idstepsshell
[jq:material-open-in-new:]: https://jqlang.org/
[fromJSON() function:material-open-in-new:]: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/evaluate-expressions-in-workflows-and-actions#fromjson
[GitHub action:material-open-in-new:]: https://docs.github.com/en/actions/sharing-automations/creating-actions/about-custom-actions
[GitHub actions inputs:material-open-in-new:]: https://docs.github.com/en/actions/sharing-automations/creating-actions/metadata-syntax-for-github-actions#inputs
[GitHub marketplace:material-open-in-new:]: https://github.com/marketplace
[HERE doc:material-open-in-new:]: https://linuxize.com/post/bash-heredoc/
[set -e:material-open-in-new:]: https://www.gnu.org/savannah-checkouts/gnu/bash/manual/bash.html#The-Set-Builtin
[ternary operator:material-open-in-new:]: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/evaluate-expressions-in-workflows-and-actions#operators
