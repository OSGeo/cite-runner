from ogc_cite_runner.parsers import earl


def test_parse_test_suite_result_ogcapi_features_1_0(
    ogcapi_features_1_0_response_element,
):
    response = earl.parse_test_suite_result(ogcapi_features_1_0_response_element)
    assert response.suite_title == "ogcapi-features-1.0-1.6"
    assert response.num_tests_total == 282
    assert response.num_failed_tests == 12
    assert response.num_skipped_tests == 6
    assert response.num_passed_tests == 264
    assert not response.passed
    assert len(response.conformance_class_results) == 2
    crs_conf_class = response.conformance_class_results[0]
    assert crs_conf_class.title == "Coordinate Reference Systems by Reference"
    assert crs_conf_class.num_failed_tests == 0
    assert crs_conf_class.num_skipped_tests == 4
    assert crs_conf_class.num_passed_tests == 41
    core_conf_class = response.conformance_class_results[1]
    assert core_conf_class.title == "Core"
    assert core_conf_class.num_failed_tests == 12
    assert core_conf_class.num_skipped_tests == 2
    assert core_conf_class.num_passed_tests == 223


def test_parse_test_suite_result_ogcapi_processes_1_0(
    ogcapi_processes_1_0_response_element,
):
    response = earl.parse_test_suite_result(ogcapi_processes_1_0_response_element)
    assert response.suite_title == "ogcapi-processes-1.0-1.0"
    assert response.num_tests_total == 54
    assert response.num_failed_tests == 0
    assert response.num_skipped_tests == 54
    assert response.num_passed_tests == 0
    assert response.passed
    assert len(response.conformance_class_results) == 3
    core_conf_class = response.conformance_class_results[0]
    assert core_conf_class.title == "Core"
    assert core_conf_class.num_failed_tests == 0
    assert core_conf_class.num_skipped_tests == 45
    assert core_conf_class.num_passed_tests == 0
    job_list_conf_class = response.conformance_class_results[1]
    assert job_list_conf_class.title == "Job List"
    assert job_list_conf_class.num_failed_tests == 0
    assert job_list_conf_class.num_skipped_tests == 2
    assert job_list_conf_class.num_passed_tests == 0
    process_description_conf_class = response.conformance_class_results[2]
    assert process_description_conf_class.title == "OGC Process Description"
    assert process_description_conf_class.num_failed_tests == 0
    assert process_description_conf_class.num_skipped_tests == 7
    assert process_description_conf_class.num_passed_tests == 0
