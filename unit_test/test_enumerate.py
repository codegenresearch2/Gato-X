@patch("gatox.enumerate.enumerate.Api")
def test_bad_token(mock_api):
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

    assert val is False