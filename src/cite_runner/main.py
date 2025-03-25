"""CLI Utilities for running CITE tests and parsing their results."""

from builtins import print as stdlib_print
import logging
import typing
from pathlib import Path

import click
import httpx
import pydantic
import typer
from rich import print

from . import (
    config,
    exceptions,
    models,
    teamengine_runner,
)

logger = logging.getLogger(__name__)
app = typer.Typer()


def _parse_pydantic_secret_str(value: str) -> pydantic.SecretStr:
    return pydantic.SecretStr(value)


_test_suite_identifier_argument = typing.Annotated[
    str, typer.Argument(help="Identifier of the test suite. Ex: ogcapi-features-1.0")
]
_teamengine_base_url_argument = typing.Annotated[
    str,
    typer.Argument(
        help="Base URL of teamengine service. Ex: http://localhost:8080/teamengine"
    ),
]
_teamengine_username_option = typing.Annotated[
    pydantic.SecretStr,
    typer.Option(
        help="Username for authenticating with teamengine",
        parser=_parse_pydantic_secret_str,
    ),
]
_teamengine_password_option = typing.Annotated[
    pydantic.SecretStr,
    typer.Option(
        help="Password for authenticating with teamengine",
        parser=_parse_pydantic_secret_str,
    ),
]


@app.callback()
def base_callback(
    ctx: typer.Context, debug: bool = False, network_timeout: int = 120
) -> None:
    config.configure_logging(debug=debug)
    ctx.obj = config.get_context(
        debug=debug,
        network_timeout_seconds=network_timeout,
    )


@app.command("parse-result")
def parse_test_result(
    ctx: typer.Context,
    test_suite_result: typing.Annotated[
        Path,
        typer.Argument(
            exists=True, file_okay=True, dir_okay=False, help="Suite execution result"
        ),
    ],
    output_format: models.ParseableOutputFormat = models.ParseableOutputFormat.JSON,
    treat_skipped_tests_as_failures: bool = True,
    exit_with_error_on_suite_failed_result: bool = False,
):
    parsed = teamengine_runner.parse_test_suite_result(
        test_suite_result.read_text(), ctx.obj.settings, treat_skipped_tests_as_failures
    )
    serialized = teamengine_runner.serialize_suite_result(
        parsed, output_format, ctx.obj.settings, ctx.obj.jinja_environment
    )
    print(serialized)
    raise typer.Exit(_get_exit_code(parsed, exit_with_error_on_suite_failed_result))


@app.command("execute-test-suite")
def execute_test_suite_from_github_actions(
    ctx: typer.Context,
    teamengine_base_url: _teamengine_base_url_argument,
    test_suite_identifier: _test_suite_identifier_argument,
    test_suite_input: typing.Annotated[
        list[str],
        typer.Argument(
            help=(
                "Space-separated list of inputs to be passed to teamengine. Each "
                "input must be formatted as key=value. Ex: "
                "iut=http://localhost:5000 noofcollections=-1"
            )
        ),
    ],
    teamengine_username: _teamengine_username_option = "ogctest",
    teamengine_password: _teamengine_password_option = "ogctest",
    treat_skipped_tests_as_failures: bool = True,
    exit_with_error_on_suite_failed_result: bool = False,
    output_format: models.OutputFormat = models.OutputFormat.MARKDOWN,
):
    """Execute a CITE test suite via github actions.

    This command presents a simpler interface to run the
    `execute-test-suite-standalone` command, making it easier to run as a
    github action.
    """
    suite_inputs = {}
    for raw_suite_input in test_suite_input:
        param_name, param_value = raw_suite_input.partition("=")[::2]
        param_values = suite_inputs.setdefault(param_name, [])
        param_values.append(param_value)
    parsed, serialized = _execute_test_suite(
        ctx.obj,
        teamengine_base_url=teamengine_base_url,
        test_suite_identifier=test_suite_identifier,
        teamengine_username=teamengine_username,
        teamengine_password=teamengine_password,
        test_suite_inputs=suite_inputs,
        output_format=output_format,
        treat_skipped_tests_as_failures=treat_skipped_tests_as_failures,
    )
    logger.debug(f"{parsed.passed=}")
    if output_format == models.OutputFormat.RAW:
        stdlib_print(serialized)
    else:
        print(serialized)
    raise typer.Exit(_get_exit_code(parsed, exit_with_error_on_suite_failed_result))


@app.command()
def execute_test_suite_standalone(
    ctx: typer.Context,
    teamengine_base_url: _teamengine_base_url_argument,
    test_suite_identifier: _test_suite_identifier_argument,
    teamengine_username: _teamengine_username_option = "ogctest",
    teamengine_password: _teamengine_password_option = "ogctest",
    test_suite_input: typing.Annotated[
        typing.Optional[list[click.Tuple]],
        typer.Option(
            click_type=click.Tuple([str, str]),
            help=(
                "Input name and value separated by a space. "
                "Ex: --test-suite-input iut http://localhost:5000"
            ),
        ),
    ] = None,
    output_format: models.OutputFormat = models.OutputFormat.MARKDOWN,
    treat_skipped_tests_as_failures: bool = True,
    exit_with_error_on_suite_failed_result: bool = False,
):
    """Execute a CITE test suite."""
    suite_inputs = {}
    for param_name, param_value in test_suite_input:
        param_values = suite_inputs.setdefault(param_name, [])
        param_values.append(param_value)
    parsed, serialized = _execute_test_suite(
        ctx.obj,
        teamengine_base_url=teamengine_base_url,
        test_suite_identifier=test_suite_identifier,
        teamengine_username=teamengine_username,
        teamengine_password=teamengine_password,
        test_suite_inputs=suite_inputs,
        output_format=output_format,
        treat_skipped_tests_as_failures=treat_skipped_tests_as_failures,
    )
    if output_format == models.OutputFormat.RAW:
        logger.debug("Outputting raw response, as returned by teamengine...")
        stdlib_print(serialized)
    else:
        print(serialized)
    raise typer.Exit(_get_exit_code(parsed, exit_with_error_on_suite_failed_result))


def _execute_test_suite(
    ctx: config.CliContext,
    teamengine_base_url: str,
    test_suite_identifier: str,
    teamengine_username: pydantic.SecretStr,
    teamengine_password: pydantic.SecretStr,
    test_suite_inputs: dict[str, list[str]],
    output_format: models.OutputFormat,
    treat_skipped_tests_as_failures: bool,
) -> tuple[models.TestSuiteResult, str]:
    logger.debug(f"{locals()=}")
    client = httpx.Client(timeout=ctx.network_timeout_seconds)
    base_url = teamengine_base_url.strip("/")
    if teamengine_runner.wait_for_teamengine_to_be_ready(client, base_url):
        logger.debug(
            f"Asking teamengine to execute test suite {test_suite_identifier!r}..."
        )
        try:
            raw_result = teamengine_runner.execute_test_suite(
                client,
                base_url,
                test_suite_identifier,
                test_suite_arguments=test_suite_inputs,
                teamengine_username=teamengine_username,
                teamengine_password=teamengine_password,
            )
        except exceptions.CiteRunnerException:
            logger.exception("Unable to collect test suite execution results")
            raise SystemExit(1)
        else:
            parsed = teamengine_runner.parse_test_suite_result(
                raw_result, ctx.settings, treat_skipped_tests_as_failures
            )
            if output_format == models.OutputFormat.RAW:
                logger.debug("Outputting raw response, as returned by teamengine...")
                serialized = raw_result
            else:
                logger.debug("Parsing test suite execution results...")
                format_to_output = models.ParseableOutputFormat(output_format.value)
                serialized = teamengine_runner.serialize_suite_result(
                    parsed, format_to_output, ctx.settings, ctx.jinja_environment
                )
            return parsed, serialized
    else:
        logger.critical("teamengine service is not available")
        raise SystemExit(1)


def _get_exit_code(
    parsed: models.TestSuiteResult, exit_with_error_on_suite_failed_result: bool
) -> int:
    return 0 if parsed.passed else (1 if exit_with_error_on_suite_failed_result else 0)
