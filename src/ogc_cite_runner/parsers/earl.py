"""Utilities for parsing test suite results that use EARL.

EARL is the W3C Evaluation and Report Language. It defines a vocabulary for
expressing test results. More info:

https://www.w3.org/TR/EARL10-Schema

"""

import datetime as dt

from isodate import parse_duration
from lxml import etree

from .. import models
from ..teamengine_runner import logger


def parse_test_suite_result(
    suite_result: etree.Element,
) -> models.TestSuiteResult:
    """Parse test suite result from EARL."""
    test_run_el = suite_result.find("./cite:TestRun", namespaces=suite_result.nsmap)
    suite_title = test_run_el.find("dct:title", namespaces=suite_result.nsmap).text
    raw_passed = test_run_el.find(
        "cite:areCoreConformanceClassesPassed", namespaces=suite_result.nsmap
    ).text
    passed = True if raw_passed.upper() == "TRUE" else False
    suite_identifier = test_run_el.find(
        "dct:identifier", namespaces=suite_result.nsmap
    ).text
    test_run_start = _parse_to_datetime(
        test_run_el.find("dct:created", namespaces=suite_result.nsmap).text
    )
    test_run_duration = parse_duration(
        test_run_el.find("dct:extent", namespaces=suite_result.nsmap).text
    )
    test_run_end = test_run_start + test_run_duration
    num_passed = int(
        test_run_el.find("cite:testsPassed", namespaces=suite_result.nsmap).text
    )
    num_failed = int(
        test_run_el.find("cite:testsFailed", namespaces=suite_result.nsmap).text
    )
    num_skipped = int(
        test_run_el.find("cite:testsSkipped", namespaces=suite_result.nsmap).text
    )
    suite_inputs = _parse_test_inputs(test_run_el, suite_result.nsmap)
    conf_classes = _parse_test_requirements(test_run_el, suite_result.nsmap)
    for assertion_el in suite_result.findall(
        "earl:Assertion", namespaces=suite_result.nsmap
    ):
        test_case_result = _parse_assertion(assertion_el, suite_result.nsmap)
        for conf_class_result, conf_class_parts in conf_classes:
            if test_case_result.identifier in conf_class_parts:
                conf_class_result.tests.append(test_case_result)
                break
        else:
            print(
                f"test case {test_case_result.identifier} is not part of any "
                f"conformance class"
            )
            logger.warning(
                f"test case {test_case_result.identifier} is not part of any "
                f"conformance class"
            )
    return models.TestSuiteResult(
        suite_identifier=suite_identifier,
        suite_title=suite_title,
        test_run_start=test_run_start,
        test_run_duration=test_run_duration,
        test_run_end=test_run_end,
        num_tests_total=num_passed + num_failed + num_skipped,
        num_failed_tests=num_failed,
        num_skipped_tests=num_skipped,
        num_passed_tests=num_passed,
        inputs=suite_inputs,
        conformance_class_results=[c[0] for c in conf_classes],
        passed=passed,
    )


def _parse_test_inputs(
    test_run_el: etree.Element, nsmap: dict
) -> list[models.TestSuiteInput]:
    suite_inputs = []
    for test_suite_input_el in test_run_el.findall(
        "cite:inputs/rdf:Bag/rdf:li", namespaces=nsmap
    ):
        suite_inputs.append(
            models.TestSuiteInput(
                name=test_suite_input_el.find("dct:title", namespaces=nsmap).text,
                value=test_suite_input_el.find(
                    "dct:description", namespaces=nsmap
                ).text,
            )
        )
    return suite_inputs


def _parse_test_requirements(
    test_run_el: etree.Element, nsmap: dict
) -> list[tuple[models.ConformanceClassResult, list[str]]]:
    conf_classes = []
    for test_requirement_el in test_run_el.findall(
        "cite:requirements/rdf:Seq/rdf:li/earl:TestRequirement", namespaces=nsmap
    ):
        title = test_requirement_el.find("dct:title", namespaces=nsmap).text
        try:
            description = test_requirement_el.find(
                "dct:description", namespaces=nsmap
            ).text
        except AttributeError:
            description = ""
        num_failed = int(
            test_requirement_el.find("cite:testsFailed", namespaces=nsmap).text
        )
        num_passed = int(
            test_requirement_el.find("cite:testsPassed", namespaces=nsmap).text
        )
        num_skipped = int(
            test_requirement_el.find("cite:testsSkipped", namespaces=nsmap).text
        )
        parts = []
        for part_el in test_requirement_el.findall("dct:hasPart", namespaces=nsmap):
            try:
                part_id = part_el.attrib[f"{{{nsmap['rdf']}}}resource"]
                parts.append(part_id)
            except KeyError:
                test_case_el = part_el.find("earl:TestCase", namespaces=nsmap)
                part_id = test_case_el.attrib[f"{{{nsmap['rdf']}}}about"]
                parts.append(part_id)
        conf_class_result = models.ConformanceClassResult(
            title=title,
            description=description,
            num_failed_tests=num_failed,
            num_passed_tests=num_passed,
            num_skipped_tests=num_skipped,
            tests=[],
        )
        conf_classes.append((conf_class_result, parts))
    conf_classes.sort(key=lambda item: item[0].title)
    return conf_classes


def _parse_assertion(assertion_el: etree.Element, nsmap: dict) -> models.TestCaseResult:
    raw_outcome = assertion_el.find(
        "earl:result/earl:TestResult/earl:outcome", namespaces=nsmap
    ).attrib[f"{{{nsmap['rdf']}}}resource"]
    outcome = raw_outcome.split("earl#")[-1]
    test_status = {
        "cantTell": models.TestStatus.CANT_TELL,
        "failed": models.TestStatus.FAILED,
        "inapplicable": models.TestStatus.SKIPPED,
        "passed": models.TestStatus.PASSED,
        "untested": models.TestStatus.SKIPPED,
    }[outcome]

    try:
        test_identifier = assertion_el.find("earl:test", namespaces=nsmap).attrib[
            f"{{{nsmap['rdf']}}}resource"
        ]
    except KeyError:
        test_identifier = assertion_el.find(
            "earl:test/earl:TestCase", namespaces=nsmap
        ).attrib[f"{{{nsmap['rdf']}}}about"]
    title = (
        title_el.text
        if (
            title_el := assertion_el.find(
                "earl:test/earl:TestCase/dct:title", namespaces=nsmap
            )
        )
        is not None
        else None
    )
    description = (
        description_el.text
        if (
            description_el := assertion_el.find(
                "earl:test/earl:TestCase/dct:description", namespaces=nsmap
            )
        )
        is not None
        else None
    )
    test_detail = None
    if test_status in (
        models.TestStatus.CANT_TELL,
        models.TestStatus.FAILED,
        models.TestStatus.SKIPPED,
    ):
        test_detail = assertion_el.find(
            "earl:result/earl:TestResult/dct:description", namespaces=nsmap
        ).text
    return models.TestCaseResult(
        identifier=test_identifier,
        status=test_status,
        detail=test_detail,
        name=title,
        description=description,
    )


def _parse_to_datetime(temporal_value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(temporal_value.strip("Z")).replace(
        tzinfo=dt.timezone.utc
    )
