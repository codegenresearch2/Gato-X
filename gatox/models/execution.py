import datetime

from gatox.models.organization import Organization
from gatox.models.repository import Repository

class Execution:
    """Simple wrapper class to provide accessor methods against a full Gato
    execution run.
    """

    def __init__(self):
        """Initialize wrapper class."""
        self.user_details = None
        self.organizations = []
        self.repositories = []
        self.timestamp = datetime.datetime.now()

    def add_organizations(self, organizations):
        """Add list of organization wrapper objects.

        Args:
            organizations (List[Organization]): List of org wrappers.
        """
        if isinstance(organizations, list) and all(isinstance(org, Organization) for org in organizations):
            self.organizations = organizations
        else:
            raise ValueError("Input must be a list of Organization objects")

    def add_repositories(self, repositories):
        """Add list of repository wrapper objects.

        Args:
            repositories (List[Repository]): List of repo wrappers.
        """
        if isinstance(repositories, list) and all(isinstance(repo, Repository) for repo in repositories):
            self.repositories = repositories
        else:
            raise ValueError("Input must be a list of Repository objects")

    def set_user_details(self, user_details):
        """Set details about the user's permissions.

        Args:
            user_details (dict): Details about the user's permissions.
        """
        if isinstance(user_details, dict):
            self.user_details = user_details
        else:
            raise ValueError("Input must be a dictionary")

    def toJSON(self):
        """Converts the run to Gato JSON representation"""
        if self.user_details:
            try:
                representation = {
                    "username": self.user_details["user"],
                    "scopes": self.user_details["scopes"],
                    "enumeration": {
                        "timestamp": self.timestamp.ctime(),
                        "organizations": [org.toJSON() for org in self.organizations],
                        "repositories": [repo.toJSON() for repo in self.repositories],
                    },
                }
                return representation
            except Exception as e:
                print(f"An error occurred: {e}")
        else:
            print("User details are not set")