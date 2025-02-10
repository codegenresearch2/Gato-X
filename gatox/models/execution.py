import datetime

from gatox.models.organization import Organization
from gatox.models.organization import Repository


class Execution:
    """Simple wrapper class to provide accessor methods against a full Gato
    execution run.
    """

    def __init__(self):
        """Initialize wrapper class."""
        self.user_details = None
        self.organizations: list[Organization] = []
        self.repositories: list[Repository] = []
        self.timestamp = datetime.datetime.now()

    def add_organizations(self, organizations: list[Organization]):
        """Add list of organization wrapper objects.

        Args:
            organizations (List[Organization]): List of org wrappers.
        """
        if organizations:
            self.organizations = organizations

    def add_repositories(self, repositories: list[Repository]):
        """Add list of repository wrapper objects.

        Args:
            repositories (List[Repository]): List of repo wrappers.
        """
        if repositories:
            self.repositories = repositories

    def set_user_details(self, user_details):
        """Set user details.

        Args:
            user_details (dict): Details about the user's permissions.
        """
        self.user_details = user_details

    def toJSON(self):
        """Converts the run to Gato JSON representation"""
        if self.user_details:
            representation = {
                "username": self.user_details["user"],
                "scopes": self.user_details["scopes"],
                "enumeration": {
                    "timestamp": self.timestamp.ctime(),
                    "organizations": [
                        organization.toJSON() for organization in self.organizations
                    ],
                    "repositories": [
                        repository.toJSON() for repository in self.repositories
                    ],
                },
            }

            return representation
        else:
            return {}

    def enumerate_repositories(self, api, user_details):
        """Enumerate repositories for the user.

        Args:
            api (Api): GitHub API wrapper object.
            user_details (dict): Details about the user's permissions.
        """
        self.set_user_details(user_details)
        orgs = api.get_user_organizations(user_details["user"])
        repos = api.get_user_repositories(user_details["user"])

        org_wrappers = []
        repo_wrappers = []

        for org in orgs:
            org_wrapper = Organization(org, user_details["scopes"])
            org_wrappers.append(org_wrapper)

        for repo in repos:
            repo_wrapper = Repository(repo, user_details["scopes"])
            repo_wrappers.append(repo_wrapper)

        self.add_organizations(org_wrappers)
        self.add_repositories(repo_wrappers)

    def enumerate_repository_secrets(self, api):
        """Enumerate secrets accessible to the repositories.

        Args:
            api (Api): GitHub API wrapper object.
        """
        for repo_wrapper in self.repositories:
            api.enumerate_repository_secrets(repo_wrapper)