from typing import List
from gatox.models.organization import Organization
from gatox.models.repository import Repository
from gatox.github.api import Api


class OrganizationEnum:
    """Helper class to wrap organization specific enumeration functionality."""

    def __init__(self, api: Api):
        """Simple init method.

        Args:
            api (Api): Instantiated GitHub API wrapper object.
        """
        self.api = api

    def __assemble_repo_list(self, organization: str, visibilities: list) -> List[Repository]:
        """Get a list of repositories that match the visibility types.

        Args:
            organization (str): Name of the organization.
            visibilities (list): List of visibilities (public, private, etc)
        """
        repos = []
        for visibility in visibilities:
            raw_repos = self.api.check_org_repos(organization, visibility)
            if raw_repos:
                repos.extend([Repository(repo) for repo in raw_repos])
        return repos

    def construct_repo_enum_list(self, organization: Organization) -> List[Repository]:
        """Constructs a list of repositories that a user has access to within an organization.

        Args:
            organization (Organization): Organization wrapper object.

        Returns:
            List[Repository]: List of repositories to enumerate.
        """
        org_private_repos = self.__assemble_repo_list(organization.name, ['private', 'internal'])
        org_public_repos = self.__assemble_repo_list(organization.name, ['public'])

        organization.set_public_repos(org_public_repos)
        organization.set_private_repos(org_private_repos)

        # Check for SSO if private repositories are present
        if org_private_repos:
            organization.sso_enabled = self.api.validate_sso(organization.name, org_private_repos[0].name)

        return org_public_repos + org_private_repos
