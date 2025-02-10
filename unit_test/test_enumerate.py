import os
import pathlib
import pytest
import json
from unittest.mock import patch, MagicMock
from gatox.models.repository import Repository
from gatox.enumerate.enumerate import Enumerator
from gatox.cli.output import Output

# Initialize output
Output(True)

# Global variables
TEST_REPO_DATA = None
TEST_WORKFLOW_YML = None
TEST_ORG_DATA = None

# Fixture to load test files
@pytest.fixture(scope="session", autouse=True)
def load_test_files(request):
    global TEST_REPO_DATA, TEST_WORKFLOW_YML, TEST_ORG_DATA
    curr_path = pathlib.Path(__file__).parent.resolve()
    test_repo_path = os.path.join(curr_path, "files/example_repo.json")
    test_org_path = os.path.join(curr_path, "files/example_org.json")
    test_wf_path = os.path.join(curr_path, "files/main.yaml")

    with open(test_repo_path, "r") as repo_data:
        TEST_REPO_DATA = json.load(repo_data)

    with open(test_org_path, "r") as org_data:
        TEST_ORG_DATA = json.load(org_data)

    with open(test_wf_path, "r") as wf_data:
        TEST_WORKFLOW_YML = wf_data.read()

@patch("gatox.enumerate.enumerate.Api")
def test_bad_token(mock_api, capsys):
    """Test the behavior when an invalid token is used."""
    gh_enumeration_runner = Enumerator(
        "ghp_BADTOKEN",
        socks_proxy=None,
        http_proxy=None,
        output_yaml=False,
        skip_log=True,
    )

    mock_api.return_value.is_app_token.return_value = False
    mock_api.return_value.check_user.return_value = None

    val = gh_enumeration_runner.self_enumeration()

    captured = capsys.readouterr()
    assert "The user is not authenticated!" in captured.out
    assert val is False