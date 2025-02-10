import pytest
import os
import pathlib
from unittest.mock import patch, mock_open
from gatox.workflow_parser.workflow_parser import WorkflowParser
from gatox.models.workflow import Workflow
from gatox.workflow_parser.utility import check_sus

TEST_WF = """
# Test workflow content
"""

# Added methods for better code organization
def get_workflow_parser(workflow_content):
    workflow = Workflow('unit_test', workflow_content, 'main.yml')
    return WorkflowParser(workflow)

def get_test_repo_path():
    curr_path = pathlib.Path(__file__).parent.resolve()
    return os.path.join(curr_path, "files/")

def mock_open_file(mock_file, data=""):
    mock_file.return_value = mock_open(read_data=data).return_value

def assert_file_write(mock_file, expected_data):
    mock_file().write.assert_called_once_with(expected_data)

def test_parse_workflow():
    parser = get_workflow_parser(TEST_WF)
    sh_list = parser.self_hosted()
    assert len(sh_list) > 0

def test_workflow_write():
    parser = get_workflow_parser(TEST_WF)
    test_repo_path = get_test_repo_path()

    with patch("builtins.open", mock_open) as mock_file:
        mock_open_file(mock_file)
        parser.output(test_repo_path)
        assert_file_write(mock_file, parser.raw_yaml)

def test_check_injection_no_vulnerable_triggers():
    parser = get_workflow_parser(TEST_WF)
    with patch.object(parser, 'get_vulnerable_triggers', return_value=[]):
        result = parser.check_injection()
        assert result == {}

def test_check_injection_no_job_contents():
    parser = get_workflow_parser(TEST_WF5)
    result = parser.check_injection()
    assert result == {}

def test_check_injection_no_step_contents():
    parser = get_workflow_parser(TEST_WF6)
    result = parser.check_injection()
    assert result == {}

def test_check_injection_comment():
    parser = get_workflow_parser(TEST_WF3)
    result = parser.check_injection()
    assert 'updatesnapshots' in result

def test_check_injection_no_tokens():
    parser = get_workflow_parser(TEST_WF)
    result = parser.check_injection()
    assert result == {}

def test_check_pwn_request():
    parser = get_workflow_parser(TEST_WF4)
    result = parser.check_pwn_request()
    assert result['candidates']