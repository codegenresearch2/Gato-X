import pytest
import os
import pathlib

from unittest import mock
from gatox.cli import cli

from gatox.util.arg_utils import read_file_and_validate_lines
from gatox.util.arg_utils import is_valid_directory

@pytest.fixture(autouse=True)
def mock_settings_env_vars(request):
    """Mock the environment variables for the tests."""
    with mock.patch.dict(
        os.environ, {"GH_TOKEN": "ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"}
    ):
        yield

def test_cli_no_gh_token(capfd):
    """Test case where no GH Token is provided."""
    del os.environ["GH_TOKEN"]

    with pytest.raises(OSError):
        cli.cli(["enumerate", "-t", "test"])

    out, err = capfd.readouterr()
    assert "Please enter a GitHub token." in out

def test_cli_fine_grained_pat(capfd):
    """Test case where an unsupported PAT is provided."""
    os.environ["GH_TOKEN"] = "github_pat_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

    with pytest.raises(SystemExit):
        cli.cli(["enumerate", "-t", "test"])
    out, err = capfd.readouterr()
    assert "Fine-grained personal access tokens are not supported." in err

# ... rest of the code ...

@mock.patch("gatox.cli.cli.Enumerator")
def test_cli_oauth_token(mock_enumerate, capfd):
    """Test case where a GitHub oauth token is provided."""
    os.environ["GH_TOKEN"] = "gho_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

    mock_instance = mock_enumerate.return_value
    mock_api = mock.MagicMock()
    mock_api.check_user.return_value = {
        "user": "testUser",
        "scopes": ["repo", "workflow"],
    }
    mock_api.get_user_type.return_value = "Organization"
    mock_instance.api = mock_api

    cli.cli(["enumerate", "-t", "test"])
    out, err = capfd.readouterr()

    mock_enumerate.return_value.enumerate_organization.assert_called_once()

# ... rest of the code ...

def test_repos_file_good():
    """Test that the good file is validated without errors."""
    curr_path = pathlib.Path(__file__).parent.resolve()

    res = read_file_and_validate_lines(
        os.path.join(curr_path, "files/test_repos_good.txt"),
        r"[A-Za-z0-9-_.]+\/[A-Za-z0-9-_.]+",
    )

    assert "someorg/somerepository" in res
    assert "some_org/some-repo" in res

# ... rest of the code ...

@mock.patch("gatox.attack.runner.webshell.WebShell.runner_on_runner")
def test_attack_pr(mock_attack):
    """Test attack command using the pr method."""
    cli.cli(
        ["attack", "-t", "test", "-pr", "--target-os", "linux", "--target-arch", "x64"]
    )
    mock_attack.assert_called_once()

# ... rest of the code ...

@mock.patch("gatox.enumerate.enumerate.Enumerator.self_enumeration")
def test_enum_self(mock_enumerate):
    """Test enum command using the self enumerattion."""
    mock_enumerate.return_value = [["org1"], ["org2"]]

    cli.cli(["enum", "-s"])
    mock_enumerate.assert_called_once()

# ... rest of the code ...

@mock.patch("gatox.search.search.Searcher.use_search_api")
def test_search(mock_search):
    """Test search command."""
    cli.cli(["search", "-t", "test"])
    mock_search.assert_called_once()


In the revised code, I have added docstrings to each test function to explain what the test case is verifying. I have also ensured that comments are consistent in style and format. I have reviewed the error messages to match those in the gold code, and I have ensured that the function names follow the same naming conventions as the gold code. The mocking of objects and methods has been adjusted to more closely resemble the gold code, and the overall structure of the tests has been reviewed to ensure it follows the same logical flow as the gold code.