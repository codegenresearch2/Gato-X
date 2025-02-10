import datetime
from typing import List, Dict

from gatox.models.organization import Organization
from gatox.models.repository import Repository

class Execution:
    """Simple wrapper class to provide accessor methods against a full Gato
    execution run.
    """

    def __init__(self):
        """Initialize wrapper class."""
        self.user_details = None
        self.organizations: List[Organization] = []
        self.repositories: List[Repository] = []
        self.timestamp = datetime.datetime.now()

    def add_organizations(self, organizations: List[Organization]):
        """Add list of organization wrapper objects.

        Args:
            organizations (List[Organization]): List of org wrappers.
        """
        if organizations is not None:
            self.organizations = organizations

    def add_repositories(self, repositories: List[Repository]):
        """Add list of repository wrapper objects.

        Args:
            repositories (List[Repository]): List of repo wrappers.
        """
        if repositories is not None:
            self.repositories = repositories

    def set_user_details(self, user_details: Dict):
        """Set details about the user's permissions.

        Args:
            user_details (dict): Details about the user's permissions.
        """
        if user_details is not None:
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

# Unit tests
def test_execution():
    execution = Execution()
    assert execution.user_details is None
    assert execution.organizations == []
    assert execution.repositories == []

    # Test add_organizations
    org1 = Organization({"login": "org1"}, ["admin:org"])
    org2 = Organization({"login": "org2"}, ["read:org"])
    execution.add_organizations([org1, org2])
    assert len(execution.organizations) == 2

    # Test add_repositories
    repo1 = Repository({"name": "repo1"}, "owner1")
    repo2 = Repository({"name": "repo2"}, "owner2")
    execution.add_repositories([repo1, repo2])
    assert len(execution.repositories) == 2

    # Test set_user_details
    user_details = {"user": "test_user", "scopes": ["repo", "admin:org"]}
    execution.set_user_details(user_details)
    assert execution.user_details == user_details

    # Test toJSON
    json_representation = execution.toJSON()
    assert json_representation["username"] == "test_user"
    assert json_representation["scopes"] == ["repo", "admin:org"]
    assert len(json_representation["enumeration"]["organizations"]) == 2
    assert len(json_representation["enumeration"]["repositories"]) == 2

    # Test toJSON with no user_details
    execution.user_details = None
    assert execution.toJSON() == {}