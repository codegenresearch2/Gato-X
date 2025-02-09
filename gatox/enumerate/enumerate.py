import logging
import time

from gatox.github.api import Api
from gatox.github.gql_queries import GqlQueries
from gatox.models.repository import Repository
from gatox.models.organization import Organization
from gatox.cli.output import Output
from gatox.enumerate.repository import RepositoryEnum
from gatox.enumerate.organization import OrganizationEnum
from gatox.enumerate.recommender import Recommender
from gatox.enumerate.ingest.ingest import DataIngestor
from gatox.caching.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class Enumerator:
    """Class holding all high level logic for enumerating GitHub, whether it is
a user's entire access, individual organizations, or repositories."""

    def __init__(self,
        pat: str,
        socks_proxy: str = None,
        http_proxy: str = None,
        output_yaml: str = None,
        skip_log: bool = False,
        github_url: str = None,
        output_json: str = None
    ):
        """Initialize enumeration class with arguments sent by user.

        Args:
            pat (str): GitHub personal access token
            socks_proxy (str, optional): Proxy settings for SOCKS proxy.
            Defaults to None.
            http_proxy (str, optional): Proxy gettings for HTTP proxy.
            Defaults to None.
            output_yaml (str, optional): If set, directory to save all yml
            files to . Defaults to None.
            skip_log (bool, optional): If set, then run logs will not be
            downloaded.
            output_json (str, optional): JSON file to output enumeration
            results."
        """
        self.api = Api(
            pat,
            socks_proxy=socks_proxy,
            http_proxy=http_proxy,
            github_url=github_url,
        )

        self.socks_proxy = socks_proxy
        self.http_proxy = http_proxy
        self.skip_log = skip_log
        self.output_yaml = output_yaml
        self.user_perms = None
        self.github_url = github_url
        self.output_json = output_json

        self.repo_e = RepositoryEnum(self.api, skip_log, output_yaml)
        self.org_e = OrganizationEnum(self.api)

    def __setup_user_info(self):
        if not self.user_perms:
            self.user_perms = self.api.check_user()
            if not self.user_perms:
                Output.error("This token cannot be used for enumeration!")
                return False

            Output.info(
                "The authenticated user is: "
                f"{Output.bright(self.user_perms['user'])}"
            )
            if len(self.user_perms["scopes"]):
                Output.info(
                    "The GitHub Classic PAT has the following scopes: "
                    f'{Output.yellow(", ".join(self.user_perms[