import json

from .. import (
    config,
    models,
)


def to_markdown(
    parsed_result: models.TestSuiteResult,
    serialization_details: models.SerializationDetails,
    context: config.OGCCiteRunnerContext,
) -> str:
    """Serialize parsed test suite results to markdown"""
    template = context.jinja_environment.get_template(
        context.settings.simple_serializer_template
    )
    return template.render(
        result=parsed_result,
        serialization_details=serialization_details,
        disclaimer=context.settings.disclaimer,
        docs_url=context.settings.docs_url,
    )


def to_json(
    parsed_result: models.TestSuiteResult,
    serialization_details: models.SerializationDetails,
    context: config.OGCCiteRunnerContext,
) -> str:
    serialized = parsed_result.model_dump_json(warnings="error")
    reparsed = json.loads(serialized)
    reparsed["ogc_cite_runner"] = {
        "disclaimer": context.settings.disclaimer,
        "url": context.settings.docs_url,
    }
    return json.dumps(reparsed)
