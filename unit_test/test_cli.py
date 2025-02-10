import pytest
import os
import pathlib

from unittest import mock
from gatox.cli import cli

from gatox.util.arg_utils import read_file_and_validate_lines
from gatox.util.arg_utils import is_valid_directory

@pytest.fixture(autouse=True)
def mock_settings_env_vars(request):
    with mock.patch.dict(
        os.environ, {"GH_TOKEN": "ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"}
    ):
        yield

def test_cli_no_gh_token(capfd):
    del os.environ["GH_TOKEN"]
    try:
        cli.cli(["enumerate", "-t", "test"])
    except OSError:
        out, err = capfd.readouterr()
        assert "Please enter" in out

def test_cli_fine_grained_pat(capfd):
    os.environ["GH_TOKEN"] = "github_pat_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    try:
        cli.cli(["enumerate", "-t", "test"])
    except SystemExit:
        out, err = capfd.readouterr()
        assert "not supported" in err

def test_cli_s2s_token(capfd):
    os.environ["GH_TOKEN"] = "ghs_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    try:
        cli.cli(["enumerate", "-t", "test"])
    except SystemExit:
        out, err = capfd.readouterr()
        assert "not support App tokens without machine flag" in err

def test_cli_s2s_token_no_machine(capfd):
    os.environ["GH_TOKEN"] = "ghs_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    try:
        cli.cli(["enumerate", "-r", "testOrg/testRepo"])
    except SystemExit:
        out, err = capfd.readouterr()
        assert "not support App tokens without machine flag" in err

def test_cli_s2s_token_machine(capfd):
    os.environ["GH_TOKEN"] = "ghs_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    cli.cli(["enumerate", "-r", "testOrg/testRepo", "--machine"])
    out, err = capfd.readouterr()
    assert "Allowing the use of a GitHub App token for single repo enumeration" in out

def test_cli_u2s_token(capfd):
    os.environ["GH_TOKEN"] = "ghu_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    try:
        cli.cli(["enumerate", "-t", "test"])
    except SystemExit:
        out, err = capfd.readouterr()
        assert "Provided GitHub PAT is malformed or unsupported" in err

@mock.patch("gatox.cli.cli.Enumerator")
def test_cli_oauth_token(mock_enumerate, capfd):
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
    os.environ["GH_TOKEN"] = "invalid"
    try:
        cli.cli(["enumerate", "-t", "test"])
    except SystemExit:
        out, err = capfd.readouterr()
        assert "malformed" in err

def test_cli_double_proxy(capfd):
    try:
        cli.cli(["-sp", "socks", "-p", "http", "enumerate", "-t", "test"])
    except SystemExit:
        out, err = capfd.readouterr()
        assert "proxy at the same time" in err

def test_attack_bad_args1(capfd):
    try:
        cli.cli(["attack", "-t", "test"])
    except SystemExit:
        out, err = capfd.readouterr()
        assert "must select one" in err

def test_attack_bad_args2(capfd):
    curr_path = pathlib.Path(__file__).parent.resolve()
    try:
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
    except SystemExit:
        out, err = capfd.readouterr()
        assert "cannot be used with a custom" in err

def test_attack_invalid_path(capfd):
    try:
        cli.cli(["attack", "-t", "test", "-pr", "-f", "path"])
    except SystemExit:
        out, err = capfd.readouterr()
        assert "argument --custom-file/-f: The file: path does not exist!" in err

def test_repos_file_good():
    curr_path = pathlib.Path(__file__).parent.resolve()
    res = read_file_and_validate_lines(
        os.path.join(curr_path, "files/test_repos_good.txt"),
        r"[A-Za-z0-9-_.]+\/[A-Za-z0-9-_.]+",
    )
    assert "someorg/somerepository" in res
    assert "some_org/some-repo" in res

def test_repos_file_bad(capfd):
    curr_path = pathlib.Path(__file__).parent.resolve()
    try:
        cli.cli(
            ["enumerate", "-R", os.path.join(curr_path, "files/test_repos_bad.txt")]
        )
    except SystemExit:
        out, err = capfd.readouterr()
        assert "invalid repository name!" in err

def test_valid_dir():
    curr_path = pathlib.Path(__file__).parent.resolve()
    mock_parser = mock.MagicMock()
    res = is_valid_directory(mock_parser, os.path.join(curr_path, "files/"))
    assert res == os.path.join(curr_path, "files/")

def test_invalid_dir(capfd):
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
    cli.cli(
        ["attack", "-t", "test", "-pr", "--target-os", "linux", "--target-arch", "x64"]
    )
    mock_attack.assert_called_once()

@mock.patch("gatox.attack.runner.webshell.WebShell.runner_on_runner")
def test_attack_pr_bados(mock_attack, capfd):
    try:
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
    except SystemExit:
        out, err = capfd.readouterr()
        assert "invalid choice: 'solaris'" in err

@mock.patch("gatox.attack.attack.Attacker.push_workflow_attack")
def test_attack_workflow(mock_attack):
    cli.cli(["attack", "-t", "test", "-w"])
    mock_attack.assert_called_once()

@mock.patch("os.path.isdir")
def test_enum_bad_args1(mock_dircheck, capfd):
    mock_dircheck.return_value = False
    try:
        cli.cli(["enum", "-o", "invalid"])
    except SystemExit:
        out, err = capfd.readouterr()
        assert "--output-yaml/-o: The directory: invalid does not exist!" in err

def test_enum_bad_args2(capfd):
    try:
        cli.cli(["enum"])
    except SystemExit:
        out, err = capfd.readouterr()
        assert "type was specified" in err

def test_enum_bad_args3(capfd):
    try:
        cli.cli(["enum", "-t", "test", "-r", "testorg/test2"])
    except SystemExit:
        out, err = capfd.readouterr()
        assert "select one enumeration" in err

@mock.patch("gatox.enumerate.enumerate.Enumerator.self_enumeration")
def test_enum_self(mock_enumerate):
    mock_enumerate.return_value = [["org1"], ["org2"]]
    cli.cli(["enum", "-s"])
    mock_enumerate.assert_called_once()

@mock.patch("gatox.cli.cli.Enumerator")
def test_enum_org(mock_enumerate):
    mock_instance = mock_enumerate.return_value
    mock_api = mock.MagicMock()
    mock_api.check_user.return_value = {
        "user": "testUser",
        "scopes": ["repo", "workflow"],
    }
    mock_api.get_user_type.return_value = "Organization"
    mock_instance.api = mock_api
    cli.cli(["enum", "-t", "test"])
    mock_instance.enumerate_organization.assert_called_once()

@mock.patch("gatox.cli.cli.Enumerator")
def test_enum_user(mock_enumerate):
    mock_instance = mock_enumerate.return_value
    mock_api = mock.MagicMock()
    mock_api.check_user.return_value = {
        "user": "testUser",
        "scopes": ["repo", "workflow"],
    }
    mock_api.get_user_type.return_value = "User"
    mock_instance.api = mock_api
    cli.cli(["enum", "-t", "testUser"])
    mock_instance.enumerate_user.assert_called_once()

@mock.patch("gatox.enumerate.enumerate.Enumerator.enumerate_repos")
@mock.patch("gatox.util.read_file_and_validate_lines")
def test_enum_repos(mock_read, mock_enumerate):
    curr_path = pathlib.Path(__file__).parent.resolve()
    mock_read.return_value = "repos"
    cli.cli(["enum", "-R", os.path.join(curr_path, "files/test_repos_good.txt")])
    mock_read.assert_called_once()
    mock_enumerate.assert_called_once()

@mock.patch("gatox.enumerate.enumerate.Enumerator.enumerate_repos")
def test_enum_repo(mock_enumerate):
    cli.cli(["enum", "-r", "testorg/testrepo"])
    mock_enumerate.assert_called_once()

@mock.patch("gatox.search.search.Searcher.use_search_api")
def test_search(mock_search):
    cli.cli(["search", "-t", "test"])
    mock_search.assert_called_once()

def test_long_repo_name(capfd):
    repo_name = "Org/" + "A" * 80
    try:
        cli.cli(["enum", "-r", repo_name])
    except SystemExit:
        out, err = capfd.readouterr()
        assert "The maximum length is 79 characters!" in err

def test_invalid_repo_name(capfd):
    try:
        cli.cli(["enum", "-r", "RepoWithoutOrg"])
    except SystemExit:
        out, err = capfd.readouterr()
        assert "argument --repository/-r: The argument is not in the valid format!" in err

@mock.patch("gatox.util.arg_utils.os.access")
def test_unreadable_file(mock_access, capfd):
    curr_path = pathlib.Path(__file__).parent.resolve()
    mock_access.return_value = False
    try:
        cli.cli(["enum", "-R", os.path.join(curr_path, "files/bad_dir/bad_file")])
    except SystemExit:
        out, err = capfd.readouterr()
        assert " is not readable" in err

@mock.patch("gatox.util.arg_utils.os.access")
def test_unwritable_dir(mock_access, capfd):
    curr_path = pathlib.Path(__file__).parent.resolve()
    mock_access.return_value = False
    try:
        cli.cli(
            [
                "enum",
                "-r",
                "testOrg/testRepo",
                "-o",
                os.path.join(curr_path, "files/bad_dir"),
            ]
        )
    except SystemExit:
        out, err = capfd.readouterr()
        assert " is not writeable" in err