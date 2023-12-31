import pytest

from conftest import run_all_steps


@pytest.mark.parametrize(
    "config_file", [
        "openimagesv4_object_detection.py",
        "openimagesv4_object_detection_has_validation.py",
        "delta_mark_object_detection.py",
        "delta_mark_object_detection_has_validation.py",
    ]
)
def test_object_detection(init_env, config_file):
    """Run Blueoil test of object detection"""
    run_all_steps(init_env, config_file)
