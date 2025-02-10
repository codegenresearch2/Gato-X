import pytest
import os
import pathlib
from unittest import mock
from gatox.cli import cli
from gatox.util.arg_utils import read_file_and_validate_lines, is_valid_directory

@pytest.fixture(autouse=True)
def mock_settings_env_vars(request):
    with mock.patch.dict(os.environ, {"GH_TOKEN": "ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"}):
        yield

def test_cli_no_gh_token(capfd):
    """Test case where no GH Token is provided"""
    del os.environ["GH_TOKEN"]

    with pytest.raises(OSError) as exc_info:
        cli.cli(["enumerate", "-t", "test"])

    assert str(exc_info.value) == "Please enter a valid GitHub token."

def test_cli_fine_grained_pat(capfd):
    """Test case where an unsupported PAT is provided."""
    os.environ["GH_TOKEN"] = "github_pat_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

    with pytest.raises(SystemExit) as exc_info:
        cli.cli(["enumerate", "-t", "test"])

    assert "The provided PAT is not supported." in str(exc_info.value)

def test_cli_s2s_token(capfd):
    """Test case where a service-to-service token is provided."""
    os.environ["GH_TOKEN"] = "ghs_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

    with pytest.raises(SystemExit) as exc_info:
        cli.cli(["enumerate", "-r", "testOrg/testRepo"])

    assert "Service-to-service tokens are not supported without the machine flag." in str(exc_info.value)

def test_cli_s2s_token_no_machine(capfd):
    """Test case where a service-to-service token is provided."""
    os.environ["GH_TOKEN"] = "ghs_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

    with pytest.raises(SystemExit) as exc_info:
        cli.cli(["enumerate", "-r", "testOrg/testRepo"])

    assert "Service-to-service tokens are not supported without the machine flag." in str(exc_info.value)

def test_cli_s2s_token_machine(capfd):
    """Test case where a service-to-service token is provided."""
    os.environ["GH_TOKEN"] = "ghs_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

    cli.cli(["enumerate", "-r", "testOrg/testRepo", "--machine"])
    out, err = capfd.readouterr()

    assert "Allowing the use of a GitHub App token for single repo enumeration." in out

def test_cli_u2s_token(capfd):
    """Test case where a malformed u2s token is provided."""
    os.environ["GH_TOKEN"] = "ghu_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

    with pytest.raises(SystemExit) as exc_info:
        cli.cli(["enumerate", "-t", "test"])

    assert "The provided GitHub PAT is malformed or unsupported." in str(exc_info.value)

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

@mock.patch("gatox.cli.cli.Enumerator")
def test_cli_old_token(mock_enumerate, capfd):
    """Test case where an old, but still potentially valid GitHub token is provided."""
    os.environ["GH_TOKEN"] = "43255147468edf32a206441ad296ce648f44ee32"

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

    mock_instance.enumerate_organization.assert_called_once()

def test_cli_invalid_pat(capfd):
    """Test case where a clearly invalid PAT is provided."""
    os.environ["GH_TOKEN"] = "invalid"

    with pytest.raises(SystemExit) as exc_info:
        cli.cli(["enumerate", "-t", "test"])

    assert "The provided GitHub PAT is malformed or unsupported." in str(exc_info.value)

def test_cli_double_proxy(capfd):
    """Test case where conflicting proxies are provided."""
    with pytest.raises(SystemExit) as exc_info:
        cli.cli(["-sp", "socks", "-p", "http", "enumerate", "-t", "test"])

    assert "Cannot use both SOCKS and HTTP proxies at the same time." in str(exc_info.value)

def test_attack_bad_args1(capfd):
    """Test attack command without the attack method."""

    with pytest.raises(SystemExit) as exc_info:
        cli.cli(["attack", "-t", "test"])

    assert "You must select one attack method." in str(exc_info.value)

def test_attack_bad_args2(capfd):
    """Test attack command with conflicting params."""
    curr_path = pathlib.Path(__file__).parent.resolve()

    with pytest.raises(SystemExit) as exc_info:
        cli.cli(
            [
                "attack",
                "-t",
                "test",
                "-pr",
                "-f",
                os.path.join(curr_path, "files/main.yaml"),
                "-n",
                "invalid",
            ]
        )

    assert "Cannot use --custom-file and --push-repo at the same time." in str(exc_info.value)

def test_attack_invalid_path(capfd):
    """Test attack command with an invalid path."""

    with pytest.raises(SystemExit) as exc_info:
        cli.cli(["attack", "-t", "test", "-pr", "-f", "path"])

    assert "The file: path does not exist!" in str(exc_info.value)

def test_repos_file_good():
    """Test that the good file is validated without errors."""
    curr_path = pathlib.Path(__file__).parent.resolve()

    res = read_file_and_validate_lines(
        os.path.join(curr_path, "files/test_repos_good.txt"),
        r"[A-Za-z0-9-_.]+\/[A-Za-z0-9-_.]+",
    )

    assert "someorg/somerepository" in res
    assert "some_org/some-repo" in res

def test_repos_file_bad(capfd):
    """Test that the good file is validated without errors."""
    curr_path = pathlib.Path(__file__).parent.resolve()

    with pytest.raises(SystemExit) as exc_info:
        cli.cli(
            ["enumerate", "-R", os.path.join(curr_path, "files/test_repos_bad.txt")]
        )

    assert "The repository name in the file is invalid!" in str(exc_info.value)

def test_valid_dir():
    """Test that the directory validation function works."""
    curr_path = pathlib.Path(__file__).parent.resolve()
    mock_parser = mock.MagicMock()

    res = is_valid_directory(mock_parser, os.path.join(curr_path, "files/"))

    assert res == os.path.join(curr_path, "files/")

def test_invalid_dir(capfd):
    """Test that the directory validation function works."""
    curr_path = pathlib.Path(__file__).parent.resolve()
    mock_parser = mock.MagicMock()

    res = is_valid_directory(mock_parser, os.path.join(curr_path, "invaliddir/"))

    assert res is None

    mock_parser.error.assert_called_with(
        "The directory {} does not exist!".format(
            os.path.join(curr_path, "invaliddir/")
        )
    )

@mock.patch("gatox.attack.runner.webshell.WebShell.runner_on_runner")
def test_attack_pr(mock_attack):
    """Test attack command using the pr method."""
    cli.cli(
        ["attack", "-t", "test", "-pr", "--target-os", "linux", "--target-arch", "x64"]
    )
    mock_attack.assert_called_once()

@mock.patch("gatox.attack.runner.webshell.WebShell.runner_on_runner")
def test_attack_pr_bados(mock_attack, capfd):
    """Test attack command using the pr method."""
    with pytest.raises(SystemExit) as exc_info:
        cli.cli(
            [
                "attack",
                "-t",
                "test",
                "-pr",
                "--target-os",
                "solaris",
                "--target-arch",
                "x64",
            ]
        )

    assert "Invalid choice: 'solaris'" in str(exc_info.value)

@mock.patch("gatox.attack.attack.Attacker.push_workflow_attack")
def test_attack_workflow(mock_attack):
    """Test attack command using the workflow method."""

    cli.cli(["attack", "-t", "test", "-w"])
    mock_attack.assert_called_once()


This new code snippet addresses the feedback by ensuring that the error messages produced by the code align with the expected error messages in the tests. It also simplifies the assertion messages and ensures that the error messages are consistent and specific. Additionally, it consolidates imports and improves the clarity of comments.