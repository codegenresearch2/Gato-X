from typing import List
from gatox.models.runner import Runner
from gatox.models.repository import Repository
from gatox.models.secret import Secret

class Organization():
    """Wrapper object for an organization."""

    def __init__(self, org_data: dict, user_scopes: list, limited_data: bool = False):
        """Initialize the Organization object.

        Args:
            org_data (dict): Org data from GitHub API
            user_scopes (list): List of OAuth scopes that the PAT has
            limited_data (bool): Whether limited org_data is present (default: False)
        """
        self.name = None
        self.org_admin_user = False
        self.org_admin_scopes = False
        self.org_member = False
        self.secrets: List[Secret] = []
        self.runners: List[Runner] = []
        self.sso_enabled = False

        self.limited_data = limited_data

        self.public_repos = []
        self.private_repos = []

        self.name = org_data['login']

        # If fields such as billing email are populated, then the user MUST
        # be an organization owner. If not, then the user is a member (for
        # private repos) or
        if "billing_email" in org_data and \
                org_data["billing_email"] is not None:
            if "admin:org" in user_scopes:
                self.org_admin_scopes = True
            self.org_admin_user = True
            self.org_member = True
        elif "billing_email" in org_data:
            self.org_admin_user = False
            self.org_member = True
        else:
            self.org_admin_user = False
            self.org_member = False

    def set_secrets(self, secrets: List[Secret]):
        """Set organization-level secrets.

        Args:
            secrets (List[Secret]): List of secrets at the organization level.
        """
        self.secrets = secrets

    def set_public_repos(self, repos: List[Repository]):
        """Set list of public repos for the org.

        Args:
            repos (List[Repository]): List of Repository wrapper objects.
        """
        self.public_repos = repos

    def set_private_repos(self, repos: List[Repository]):
        """Set list of private repos for the org.

        Args:
            repos (List[Repository]): List of Repository wrapper objects.
        """
        self.private_repos = repos

    def set_runners(self, runners: List[Runner]):
        """Set a list of runners that the organization can access.

        Args:
            runners (List[Runner]): List of runners that are attached to the
            organization.
        """
        self.runners = runners

    def set_repository(self, repo: Repository):
        """Add a single repository to the organization.

        Args:
            repo (Repository): The repository to add.
        """
        if repo.is_private():
            self.private_repos.append(repo)
        else:
            self.public_repos.append(repo)

    def toJSON(self):
        """Converts the organization to a Gato JSON representation.

        Returns:
            dict: JSON representation of the organization.
        """
        representation = {
            "name": self.name,
            "org_admin_user": self.org_admin_user,
            "org_member": self.org_member,
            "org_runners": [runner.toJSON() for runner in self.runners],
            "org_secrets": [secret.toJSON() for secret in self.secrets],
            "sso_access": self.sso_enabled,
            "public_repos": [repository.toJSON() for repository in self.public_repos],
            "private_repos": [repository.toJSON() for repository in self.private_repos]
        }

        return representation