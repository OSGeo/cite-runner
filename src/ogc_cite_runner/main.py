"""CLI Utilities for running CITE tests and parsing their results."""

from builtins import print as stdlib_print
import logging
import typing
from pathlib import Path

import click
import httpx
import pydantic
import typer

from . import (
    config,
    exceptions,
    models,
    teamengine_runner,
)

logger = logging.getLogger(__name__)
app = typer.Typer()


_DEFAULT_OUTPUT_FORMAT = models.OutputFormat.CONSOLE
_DEFAULT_EXIT_WITH_ERROR = True
_DEFAULT_INCLUDE_SUMMARY = True
_DEFAULT_INCLUDE_FAILED = False
_DEFAULT_INCLUDE_SKIPPED = False
_DEFAULT_INCLUDE_PASSED = False


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
_output_format_option = typing.Annotated[
    models.OutputFormat,
    typer.Option(help="Output format for the suite execution result report"),
]
_exit_with_error_option = typing.Annotated[
    bool,
    typer.Option(
        "--exit-with-error/--exit-without-error",
        "-e/-E",
        help="Exit with an error code of 1 if the test suite has failed.",
    ),
]

_include_summary_option = typing.Annotated[
    bool,
    typer.Option(
        "--with-summary/--without-summary",
        "-f/-F",
        help=(
            "Include report section with test execution summary. Note that this does "
            "not apply to the RAW and JSON output formats, as these always "
            "include the full test execution report."
        ),
    ),
]

_include_failed_option = typing.Annotated[
    bool,
    typer.Option(
        "--with-failed/--without-failed",
        "-f/-F",
        help=(
            "Include report section detailing failed tests. Note that this does not "
            "apply to the RAW and JSON output formats, as these always include the "
            "full test execution report."
        ),
    ),
]

_include_skipped_option = typing.Annotated[
    bool,
    typer.Option(
        "--with-skipped/--without-skipped",
        "-f/-F",
        help=(
            "Include report section detailing skipped tests. Note that this does not "
            "apply to the RAW and JSON output formats, as these always include the "
            "full test execution report."
        ),
    ),
]

_include_passed_option = typing.Annotated[
    bool,
    typer.Option(
        "--with-passed/--without-passed",
        "-f/-F",
        help=(
            "Include report section detailing passed tests. Note that this does not "
            "apply to the RAW and JSON output formats, as these always include the "
            "full test execution report."
        ),
    ),
]


@app.callback()
def base_callback(
    ctx: typer.Context, debug: bool = False, network_timeout: int = 120
) -> None:
    context = config.get_context(
        debug=debug,
        network_timeout_seconds=network_timeout,
    )
    config.configure_logging(rich_console=context.status_console, debug=debug)
    ctx.obj = context


@app.command("parse-result")
def parse_test_result(
    ctx: typer.Context,
    test_suite_result: typing.Annotated[
        Path,
        typer.Argument(
            # exists=True,
            # file_okay=True,
            # dir_okay=False,
            allow_dash=True,
            help="Suite execution result",
        ),
    ],
    output_format: _output_format_option = _DEFAULT_OUTPUT_FORMAT,
    include_summary: _include_summary_option = _DEFAULT_INCLUDE_SUMMARY,
    include_failed: _include_failed_option = _DEFAULT_INCLUDE_FAILED,
    include_skipped: _include_skipped_option = _DEFAULT_INCLUDE_SKIPPED,
    include_passed: _include_passed_option = _DEFAULT_INCLUDE_PASSED,
    exit_with_error: _exit_with_error_option = _DEFAULT_EXIT_WITH_ERROR,
):
    context: config.OGCCiteRunnerContext = ctx.obj
    context.status_console.print("Parsing test suite execution results...")
    with click.open_file(test_suite_result) as fh:
        raw_result = fh.read()
    parsed = teamengine_runner.parse_test_suite_result(raw_result, context.settings)
    context.status_console.print(f"Serializing parsed results to {output_format}...")
    serialized = teamengine_runner.serialize_suite_result(
        parsed,
        output_format,
        serialization_details=models.SerializationDetails(
            include_summary=include_summary,
            include_failed_detail=include_failed,
            include_skipped_detail=include_skipped,
            include_passed_detail=include_passed,
        ),
        context=ctx.obj,
    )
    if output_format.print_pretty():
        context.result_console.print(serialized)
    else:
        stdlib_print(serialized)
    raise typer.Exit(_get_exit_code(parsed, exit_with_error))


@app.command()
def execute_test_suite_from_github_actions(
    ctx: typer.Context,
    teamengine_base_url: _teamengine_base_url_argument,
    test_suite_identifier: _test_suite_identifier_argument,
    suite_input: typing.Annotated[
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
    output_format: _output_format_option = _DEFAULT_OUTPUT_FORMAT,
    include_summary: _include_summary_option = _DEFAULT_INCLUDE_SUMMARY,
    include_failed: _include_failed_option = _DEFAULT_INCLUDE_FAILED,
    include_skipped: _include_skipped_option = _DEFAULT_INCLUDE_SKIPPED,
    include_passed: _include_passed_option = _DEFAULT_INCLUDE_PASSED,
    exit_with_error: _exit_with_error_option = _DEFAULT_EXIT_WITH_ERROR,
):
    """Execute a CITE test suite via github actions.

    This command presents a simpler interface to run the
    `execute-test-suite` command, making it easier to run as a github action.
    """
    suite_inputs = {}
    for raw_suite_input in suite_input:
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
        serialization_details=models.SerializationDetails(
            include_summary=include_summary,
            include_failed_detail=include_failed,
            include_skipped_detail=include_skipped,
            include_passed_detail=include_passed,
        ),
    )
    context: config.OGCCiteRunnerContext = ctx.obj
    if output_format.print_pretty():
        context.result_console.print(serialized)
    else:
        stdlib_print(serialized)
    raise typer.Exit(
        0
        if output_format == models.OutputFormat.RAW
        else _get_exit_code(parsed, exit_with_error)
    )


@app.command()
def execute_test_suite(
    ctx: typer.Context,
    teamengine_base_url: _teamengine_base_url_argument,
    test_suite_identifier: _test_suite_identifier_argument,
    teamengine_username: _teamengine_username_option = "ogctest",
    teamengine_password: _teamengine_password_option = "ogctest",
    suite_input: typing.Annotated[
        typing.Optional[list[click.Tuple]],
        typer.Option(
            click_type=click.Tuple([str, str]),
            help=(
                "Input name and value separated by a space. "
                "Ex: --suite-input iut http://localhost:5000"
            ),
        ),
    ] = None,
    output_format: _output_format_option = _DEFAULT_OUTPUT_FORMAT,
    include_summary: _include_summary_option = _DEFAULT_INCLUDE_SUMMARY,
    include_failed: _include_failed_option = _DEFAULT_INCLUDE_FAILED,
    include_skipped: _include_skipped_option = _DEFAULT_INCLUDE_SKIPPED,
    include_passed: _include_passed_option = _DEFAULT_INCLUDE_PASSED,
    exit_with_error: _exit_with_error_option = _DEFAULT_EXIT_WITH_ERROR,
):
    """Execute a CITE test suite."""
    suite_inputs = {}
    for param_name, param_value in suite_input:
        param_values = suite_inputs.setdefault(param_name, [])
        param_values.append(param_value)
    context: config.OGCCiteRunnerContext = ctx.obj
    parsed, serialized = _execute_test_suite(
        context,
        teamengine_base_url=teamengine_base_url,
        test_suite_identifier=test_suite_identifier,
        teamengine_username=teamengine_username,
        teamengine_password=teamengine_password,
        test_suite_inputs=suite_inputs,
        output_format=output_format,
        serialization_details=models.SerializationDetails(
            include_summary=include_summary,
            include_failed_detail=include_failed,
            include_skipped_detail=include_skipped,
            include_passed_detail=include_passed,
        ),
    )
    if output_format == models.OutputFormat.RAW:
        logger.debug("Outputting raw response, as returned by teamengine...")
    if output_format.print_pretty():
        context.result_console.print(serialized)
    else:
        stdlib_print(serialized)
    raise typer.Exit(
        0
        if output_format == models.OutputFormat.RAW
        else _get_exit_code(parsed, exit_with_error)
    )


def _execute_test_suite(
    context: config.OGCCiteRunnerContext,
    teamengine_base_url: str,
    test_suite_identifier: str,
    teamengine_username: pydantic.SecretStr,
    teamengine_password: pydantic.SecretStr,
    test_suite_inputs: dict[str, list[str]],
    output_format: models.OutputFormat,
    serialization_details: models.SerializationDetails,
) -> tuple[models.TestSuiteResult | None, str]:
    logger.debug(f"{locals()=}")
    client = httpx.Client(timeout=context.network_timeout_seconds)
    base_url = teamengine_base_url.strip("/")
    context.status_console.print("Checking if teamengine is ready...")
    if teamengine_runner.wait_for_teamengine_to_be_ready(client, base_url):
        context.status_console.print(
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
        except exceptions.OGCCiteRunnerException:
            logger.exception("Unable to collect test suite execution results")
            raise SystemExit(1)
        else:
            context.status_console.print(
                "Received teamengine execution result in EARL format"
            )
            parsed = None
            if output_format == models.OutputFormat.RAW:
                context.status_console.print(
                    "Outputting raw response, as returned by teamengine..."
                )
                serialized = raw_result
            else:
                context.status_console.print("Parsing test suite execution results...")
                parsed = teamengine_runner.parse_test_suite_result(
                    raw_result, context.settings
                )
                context.status_console.print(
                    f"Serializing parsed results to {output_format}..."
                )
                serialized = teamengine_runner.serialize_suite_result(
                    parsed,
                    output_format,
                    serialization_details,
                    context,
                )
            return parsed, serialized
    else:
        logger.critical("teamengine service is not available")
        raise SystemExit(1)


def _get_exit_code(
    parsed: models.TestSuiteResult, exit_with_error_on_suite_failed_result: bool
) -> int:
    return 0 if parsed.passed else (1 if exit_with_error_on_suite_failed_result else 0)
