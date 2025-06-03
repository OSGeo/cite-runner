"""Utilities for running a remote TEAMENGINE instance and getting its result."""

import importlib
import logging
import time
import typing
from lxml import etree

import httpx
import pydantic
from rich.console import RenderableType

from . import (
    config,
    exceptions,
    models,
)

logger = logging.getLogger(__name__)


class SuiteParserProtocol(typing.Protocol):
    def __call__(self, suite_result: etree.Element) -> models.TestSuiteResult: ...


class SuiteSerializerProtocol(typing.Protocol):
    def __call__(
        self,
        suite_result: models.TestSuiteResult,
        serialization_details: models.SerializationDetails,
        context: config.OGCCiteRunnerContext,
    ) -> RenderableType: ...


def wait_for_teamengine_to_be_ready(
    client: httpx.Client,
    teamengine_base_url: str,
    num_attempts: int = 10,
    wait_seconds: int = 10,
) -> bool:
    current_attempt = 1
    result = False
    while current_attempt <= num_attempts:
        try:
            response = client.get(f"{teamengine_base_url}/")
        except (httpx.HTTPError, httpx.ConnectError):
            logger.debug("teamengine is not ready yet.")
        else:
            if response.status_code == 200:
                result = True
                break
            else:
                logger.debug("teamengine is not ready yet.")
        if current_attempt == num_attempts:
            logger.error("teamengine did not become ready - aborting")
            break
        else:
            logger.debug(f"waiting {wait_seconds}s before trying again...")
            current_attempt += 1
            time.sleep(wait_seconds)
    return result


def execute_test_suite(
    client: httpx.Client,
    teamengine_base_url: str,
    test_suite_identifier: str,
    *,
    test_suite_arguments: typing.Optional[dict[str, list[str]]] = None,
    teamengine_username: pydantic.SecretStr | None = None,
    teamengine_password: pydantic.SecretStr | None = None,
) -> typing.Optional[str]:
    request_auth = (
        (teamengine_username.get_secret_value(), teamengine_password.get_secret_value())
        if teamengine_username is not None
        else None
    )
    response = client.get(
        f"{teamengine_base_url}/rest/suites/{test_suite_identifier}/run",
        params=test_suite_arguments,
        auth=request_auth,
        headers={
            "Accept": "application/rdf+xml",
        },
    )
    try:
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise exceptions.OGCCiteRunnerException("Could not execute test suite") from exc
    else:
        return response.text


def parse_test_suite_result(
    raw_result: str,
    settings: config.OGCCiteRunnerSettings,
    test_suite_identifier: str | None = None,
) -> models.TestSuiteResult:
    root_element = _parse_raw_result_as_xml(raw_result)
    parser: SuiteParserProtocol = _get_suite_result_parser(
        settings, test_suite_identifier
    )
    return parser(root_element)


def serialize_suite_result(
    parsed_suite_result: models.TestSuiteResult,
    output_format: models.OutputFormat,
    serialization_details: models.SerializationDetails,
    context: config.OGCCiteRunnerContext,
) -> str:
    serializer: SuiteSerializerProtocol = _get_suite_result_serializer(
        output_format, context.settings, parsed_suite_result.suite_title
    )
    return serializer(parsed_suite_result, serialization_details, context)


def _sanitize_test_suite_identifier(raw_identifier: str) -> str:
    return raw_identifier.translate(
        str.maketrans(
            {
                ".": "_",
                "-": "_",
            }
        )
    )


def _load_python_object(
    object_path: str,
) -> typing.Union[typing.Type, typing.Callable] | None:
    module_path, parser_name = object_path.rpartition(".")[::2]
    module = importlib.import_module(module_path)
    return getattr(module, parser_name)


def _get_suite_result_serializer(
    output_format: models.OutputFormat,
    settings: config.OGCCiteRunnerSettings,
    test_suite_identifier: str | None = None,
) -> SuiteSerializerProtocol:
    serializer_python_path = {
        output_format.JSON: settings.default_json_serializer,
        output_format.MARKDOWN: settings.default_markdown_serializer,
        output_format.CONSOLE: settings.default_console_serializer,
    }.get(output_format)
    if test_suite_identifier is not None:
        settings_key = "_".join(
            (
                _sanitize_test_suite_identifier(test_suite_identifier),
                output_format.value,
                "serializer",
            )
        )
        if (
            custom_serializer_path := getattr(settings, settings_key, None)
        ) is not None:
            serializer_python_path = custom_serializer_path
        else:
            logger.info(
                f"Could not find python path for custom serializer based on "
                f"test suite identifier {test_suite_identifier!r} - using "
                f"default serializer of {serializer_python_path!r}"
            )
    if serializer_python_path is None:
        raise NotImplementedError(
            f"no serializer available for {output_format=} and {test_suite_identifier=}"
        )
    return _load_python_object(serializer_python_path)


def _get_suite_result_parser(
    settings: config.OGCCiteRunnerSettings,
    test_suite_identifier: str | None = None,
) -> SuiteParserProtocol:
    parser_python_path = settings.default_parser
    if test_suite_identifier is not None:
        settings_key = "_".join(
            (_sanitize_test_suite_identifier(test_suite_identifier), "parser")
        )
        if (custom_parser_path := getattr(settings, settings_key, None)) is not None:
            parser_python_path = custom_parser_path
        else:
            logger.info(
                f"Could not find python path for custom parser based on test "
                f"suite with identifier {test_suite_identifier!r} - using "
                f"default parser of {parser_python_path!r}"
            )
    return _load_python_object(parser_python_path)


def _parse_raw_result_as_xml(raw_result: str) -> etree.Element:
    parser = etree.XMLParser(
        resolve_entities=False,
    )
    try:
        return etree.fromstring(raw_result.encode(), parser)
    except etree.ParseError as exc:
        raise exceptions.OGCCiteRunnerException(
            "Unable to parse test suite execution result as XML"
        ) from exc


def get_suite_name(
    result_root: etree.Element,
) -> str:
    suite_el = result_root.find("./suite")
    return suite_el.attrib.get("name", "")
