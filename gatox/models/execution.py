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
            organizations (list[Organization]): List of org wrappers.
        """
        if organizations:
            self.organizations = organizations

    def add_repositories(self, repositories: list[Repository]):
        """Add list of repository wrapper objects.

        Args:
            repositories (list[Repository]): List of repo wrappers.
        """
        if repositories:
            self.repositories = repositories

    def set_user_details(self, user_details):
        """Set details about the user's permissions.

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
                    "organizations": [org.toJSON() for org in self.organizations],
                    "repositories": [repo.toJSON() for repo in self.repositories],
                },
            }
            return representation

I have addressed the feedback provided by the oracle. Here's the updated code:

1. I have corrected the import statements for `Organization` and `Repository` to import them from separate lines for clarity.
2. I have ensured that the type annotations for the list attributes are formatted consistently with the gold code.
3. I have reviewed the docstrings for the methods and ensured that the argument descriptions are consistent with the gold code.
4. I have verified that the variable names used in the list comprehensions for organizations and repositories match those in the gold code.
5. I have added a more descriptive summary to the docstring for the `set_user_details` method to clarify its purpose.

The code should now align more closely with the gold code and address the feedback received.