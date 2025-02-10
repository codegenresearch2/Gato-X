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
    a user's entire access, individual organizations, or repositories.
    """

    def __init__(
        self,
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
            results.
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

    # ... rest of the code ...

    def enumerate_organization(self, org: str):
        """Enumerate an entire organization, and check everything relevant to
        self-hosted runner abuse that that the user has permissions to check.

        Args:
            org (str): Organization to perform enumeration on.

        Returns:
            bool: False if a failure occurred enumerating the organization.
        """

        if not self.__setup_user_info():
            return False

        details = self.api.get_organization_details(org)

        if not details:
            Output.warn(
                f"Unable to query the org: {Output.bright(org)}! Ensure the "
                "organization exists!")
            return False

        organization = Organization(details, self.user_perms['scopes'])

        Output.result(f"Enumerating the {Output.bright(org)} organization!")

        if organization.org_admin_user and organization.org_admin_scopes:
            self.org_e.admin_enum(organization)

        Recommender.print_org_findings(
            self.user_perms['scopes'], organization
        )

        enum_list = self.org_e.construct_repo_enum_list(organization)

        Output.info(
            f"About to enumerate "
            f"{len(organization.private_repos) + len(organization.public_repos)}"
            " repos within "
            f"the {organization.name} organization!"
        )

        Output.info(f"Querying and caching workflow YAML files!")
        wf_queries = GqlQueries.get_workflow_ymls(enum_list)

        for i, wf_query in enumerate(wf_queries):
            Output.info(f"Querying {i} out of {len(wf_queries)} batches!", end='\r')
            result = self.org_e.api.call_post('/graphql', wf_query)
            # Sometimes we don't get a 200, fall back in this case.
            if result.status_code == 200:
                DataIngestor.construct_workflow_cache(result.json()['data']['nodes'])
            else:
                Output.warn(
                    "GraphQL query failed, will revert to "
                    "REST workflow query for impacted repositories!"
                )
        try:
            for repo in enum_list:
                if repo.is_archived():
                    continue
                if self.skip_log and repo.is_fork():
                    continue
                Output.tabbed(
                    f"Enumerating: {Output.bright(repo.name)}!"
                )

                cached_repo = CacheManager().get_repository(repo.name)
                if cached_repo:
                    repo = cached_repo

                self.repo_e.enumerate_repository(repo, large_org_enum=len(enum_list) > 25)
                self.repo_e.enumerate_repository_secrets(repo)

                # Enhanced permission handling
                if repo.is_admin():
                    repo.set_permissions(self.api.get_repo_permissions(repo.name))

                # Improved trigger vulnerability detection
                self.repo_e.check_trigger_vulnerabilities(repo)

                Recommender.print_repo_secrets(
                    self.user_perms['scopes'],
                    repo.secrets
                )
                Recommender.print_repo_runner_info(repo)
                Recommender.print_repo_attack_recommendations(
                    self.user_perms['scopes'], repo
                )
        except KeyboardInterrupt:
            Output.warn("Keyboard interrupt detected, exiting enumeration!")

        return organization

    # ... rest of the code ...

# Modify the RepositoryEnum class to accept parameters in the constructor
class RepositoryEnum:
    """Repository specific enumeration functionality.
    """

    def __init__(self, api: Api, skip_log: bool, output_yaml):
        """Initialize enumeration class with instantiated API wrapper and CLI
        parameters.

        Args:
            api (Api): GitHub API wraper object.
            skip_log (bool): If set, then run logs will not be downloaded.
            output_yaml (str): If set, directory to save all yml files to.
        """
        self.api = api
        self.skip_log = skip_log
        self.output_yaml = output_yaml
        self.temp_wf_cache = {}

    # ... rest of the code ...


In the modified code, the `RepositoryEnum` class now accepts `api`, `skip_log`, and `output_yaml` as parameters in its constructor. This change addresses the feedback received about the `TypeError` that occurs when trying to instantiate `RepositoryEnum` with arguments.