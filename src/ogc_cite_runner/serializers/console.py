import humanize
import rich.box
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.console import (
    Group,
    RenderableType,
)
from rich.text import Text

from .. import (
    config,
    models,
)


def to_console(
    parsed_result: models.TestSuiteResult,
    serialization_details: models.SerializationDetails,
    context: config.OGCCiteRunnerContext,
) -> Group:
    overview_message = Text(
        f"Test suite has {'passed 🏅' if parsed_result.passed else 'failed ❌'}"
        f"\n\n"
        f"- Ran {parsed_result.num_tests_total} tests in "
        f"{humanize.precisedelta(parsed_result.test_run_duration)}\n"
        f"- 🔴 Failed {parsed_result.num_failed_tests} tests\n"
        f"- 🟡 Skipped {parsed_result.num_skipped_tests} tests\n"
        f"- 🟢 Passed {parsed_result.num_passed_tests} tests\n"
    )
    contents = [
        Padding(Text(context.settings.disclaimer, style="bright_yellow"), (0, 0, 1, 0)),
        overview_message,
    ]
    if serialization_details.include_summary:
        summary_table = Table(title="Conformance classes", expand=True)
        summary_table.add_column("Class")
        summary_table.add_column("🔴 Failed")
        summary_table.add_column("🟡 Skipped")
        summary_table.add_column("🟢 Passed")
        for conf_class in parsed_result.conformance_class_results:
            summary_table.add_row(
                conf_class.title,
                str(conf_class.num_failed_tests),
                str(conf_class.num_skipped_tests),
                str(conf_class.num_passed_tests),
            )
        summary_contents = Panel(summary_table, box=rich.box.SIMPLE)
        contents.append(summary_contents)
    if (
        serialization_details.include_failed_detail
        and parsed_result.num_failed_tests > 0
    ):
        failed_contents = _render_detail_section(
            parsed_result, models.TestStatus.FAILED
        )
        contents.append(failed_contents)
    if (
        serialization_details.include_skipped_detail
        and parsed_result.num_skipped_tests > 0
    ):
        skipped_contents = _render_detail_section(
            parsed_result, models.TestStatus.SKIPPED
        )
        contents.append(skipped_contents)
    if (
        serialization_details.include_passed_detail
        and parsed_result.num_passed_tests > 0
    ):
        passed_contents = _render_detail_section(
            parsed_result, models.TestStatus.PASSED
        )
        contents.append(passed_contents)
    panel_group = Group(
        Panel(Group(*contents), title=f"Test suite {parsed_result.suite_title}"),
    )
    return panel_group


def _render_detail_section(
    parsed_result: models.TestSuiteResult,
    detail_type: models.TestStatus,
) -> RenderableType:
    conf_classes_contents = []
    title = {
        models.TestStatus.PASSED: "🟢 Passed tests",
        models.TestStatus.FAILED: "🔴 Failed tests",
        models.TestStatus.SKIPPED: "🟡 Skipped tests",
    }[detail_type]
    for conf_class in parsed_result.conformance_class_results:
        comparator, outcome_color, test_case_result_generator = {
            models.TestStatus.PASSED: (
                conf_class.num_passed_tests,
                "green",
                conf_class.gen_passed_tests,
            ),
            models.TestStatus.FAILED: (
                conf_class.num_failed_tests,
                "red",
                conf_class.gen_failed_tests,
            ),
            models.TestStatus.SKIPPED: (
                conf_class.num_skipped_tests,
                "bright_yellow",
                conf_class.gen_skipped_tests,
            ),
        }[detail_type]
        if comparator > 0:
            test_case_group_content = []
            for test_case_result in test_case_result_generator():
                test_case_group_content.append(
                    Panel(
                        Group(
                            Text.assemble(
                                ("Test case: ", "yellow"), test_case_result.identifier
                            ),
                            Text.assemble(
                                ("Outcome: ", "yellow"),
                                (test_case_result.status.value, outcome_color),
                            ),
                            Text.assemble(
                                ("Description: ", "yellow"),
                                test_case_result.description or "",
                            ),
                            Text.assemble(
                                ("Detail: ", "yellow"), test_case_result.detail or ""
                            ),
                        ),
                        box=rich.box.SIMPLE,
                        title_align="left",
                    ),
                )
            conf_classes_contents.append(
                Panel(
                    Group(*test_case_group_content),
                    title=conf_class.title,
                    title_align="left",
                )
            )
    failed_contents = Panel(
        Group(*conf_classes_contents),
        title=title,
        title_align="left",
        box=rich.box.SIMPLE,
    )
    return failed_contents
