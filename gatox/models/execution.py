import datetime
from gatox.models.organization import Organization
from gatox.models.organization import Repository


class Execution:
    """Simple wrapper class to provide accessor methods against a full Gato execution run."""

    def __init__(self):
        """Initialize wrapper class."""
        self.user_details = None
        self.organizations = []
        self.repositories = []
        self.timestamp = datetime.datetime.now()

    def add_organizations(self, organizations: list[Organization]):
        """Add list of organization wrapper objects.

        Args:
            organizations (list[Organization]): List of organization wrapper objects.
        """
        if organizations:
            self.organizations = organizations

    def add_repositories(self, repositories: list[Repository]):
        """Add list of repository wrapper objects.

        Args:
            repositories (list[Repository]): List of repository wrapper objects.
        """
        if repositories:
            self.repositories = repositories

    def set_user_details(self, user_details: dict):
        """Set user details.

        Args:
            user_details (dict): Details about the user's permissions.
        """
        self.user_details = user_details

    def toJSON(self) -> dict:
        """Converts the run to Gato JSON representation."""
        if self.user_details:
            return {
                "username": self.user_details["user"],
                "scopes": self.user_details["scopes"],
                "enumeration": {
                    "timestamp": self.timestamp.ctime(),
                    "organizations": [org.toJSON() for org in self.organizations],
                    "repositories": [repo.toJSON() for repo in self.repositories],
                },
            }
        else:
            return {}

    def enumerate_repositories(self, api, user_details: dict):
        """Enumerate repositories for the user.

        Args:
            api (Api): GitHub API wrapper object.
            user_details (dict): Details about the user's permissions.
        """
        self.set_user_details(user_details)
        orgs = api.get_user_organizations(user_details["user"])
        repos = api.get_user_repositories(user_details["user"])

        org_wrappers = [Organization(org, user_details["scopes"]) for org in orgs]
        repo_wrappers = [Repository(repo, user_details["scopes"]) for repo in repos]

        self.add_organizations(org_wrappers)
        self.add_repositories(repo_wrappers)

    def enumerate_repository_secrets(self, api):
        """Enumerate secrets accessible to the repositories.

        Args:
            api (Api): GitHub API wrapper object.
        """
        for repo_wrapper in self.repositories:
            api.enumerate_repository_secrets(repo_wrapper)