import os
import pathlib
import pytest
import json
from unittest.mock import patch, MagicMock
from gatox.models.repository import Repository
from gatox.enumerate.enumerate import Enumerator
from gatox.cli.output import Output
from unit_test.utils import escape_ansi

# Constants
BASE_MOCK_RUNNER = [
    {
        "machine_name": "unittest1",
        "runner_name": "much_unit_such_test",
        "runner_type": "organization",
        "non_ephemeral": False,
        "token_permissions": {"Actions": "write"},
        "runner_group": "Default",
        "requested_labels": ["self-hosted", "Linux", "X64"],
    }
]

# Fixtures
@pytest.fixture(scope="session", autouse=True)
def load_test_files(request):
    global TEST_REPO_DATA, TEST_ORG_DATA, TEST_WORKFLOW_YML
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

# Tests
@patch("gatox.enumerate.enumerate.Api")
def test_init(mock_api):
    """Test the constructor for the enumerator."""
    gh_enumeration_runner = Enumerator(
        "ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        socks_proxy=None,
        http_proxy="localhost:8080",
        output_yaml=True,
        skip_log=False,
    )

    assert gh_enumeration_runner.http_proxy == "localhost:8080"

@patch("gatox.enumerate.enumerate.Api")
def test_self_enumerate(mock_api, capsys):
    """Test the self enumeration method."""
    mock_api.return_value.is_app_token.return_value = False
    mock_api.return_value.check_user.return_value = {
        "user": "testUser",
        "scopes": ["repo", "workflow"],
    }
    mock_api.return_value.check_organizations.return_value = []

    gh_enumeration_runner = Enumeration