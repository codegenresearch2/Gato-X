from typing import List
from multiprocessing import Process

from gatox.models.organization import Organization
from gatox.models.repository import Repository
from gatox.models.secret import Secret
from gatox.models.runner import Runner
from gatox.github.api import Api

class OrganizationEnum():
    """Helper class to wrap organization specific enumeration functionality.
    """

    def __init__(self, api: Api):
        """Simple init method.

        Args:
            api (Api): Instantiated GitHub API wrapper object.
        """
        self.api = api

    def __assemble_repo_list(
            self, organization: str, visibilities: list) -> List[Repository]:
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

    def construct_repo_enum_list(
            self, organization: Organization) -> List[Repository]:
        """Constructs a list of repositories that a user has access to within
        an organization.

        Args:
            organization (Organization): Organization wrapper object.

        Returns:
            List[Repository]: List of repositories to enumerate.
        """
        # Get private and internal repositories
        org_private_repos = self.__assemble_repo_list(
            organization.name, ['private', 'internal']
        )

        # If there are no private repositories, set the list to an empty list
        if not org_private_repos:
            org_private_repos = []
        else:
            # Validate SSO for the organization based on the first private repository
            sso_enabled = self.api.validate_sso(
                organization.name, org_private_repos[0].name
            )
            organization.sso_enabled = sso_enabled

        # Get public repositories
        org_public_repos = self.__assemble_repo_list(
            organization.name, ['public']
        )

        # Set the public and private repositories for the organization
        organization.set_public_repos(org_public_repos)
        organization.set_private_repos(org_private_repos)

        # If SSO is enabled, return all repositories; otherwise, return only public repositories
        if organization.sso_enabled:
            return org_private_repos + org_public_repos
        else:
            return org_public_repos

    def admin_enum(self, organization: Organization):
        """Enumeration tasks to perform if the user is an org admin and the
        token has the necessary scopes.
        """
        # Check if the user is an organization admin and has the necessary scopes
        if organization.org_admin_scopes and organization.org_admin_user:

            # Get organization runners
            runners = self.api.check_org_runners(organization.name)
            if runners:
                # Create Runner objects for each runner and set them for the organization
                org_runners = [
                    Runner(
                        runner['name'],
                        machine_name=None,
                        os=runner['os'],
                        status=runner['status'],
                        labels=runner['labels']
                    )
                    for runner in runners['runners']
                ]
                organization.set_runners(org_runners)

            # Get organization secrets
            org_secrets = self.api.get_org_secrets(organization.name)
            if org_secrets:
                # Create Secret objects for each secret and set them for the organization
                org_secrets = [
                    Secret(secret, organization.name) for secret in org_secrets
                ]

                organization.set_secrets(org_secrets)