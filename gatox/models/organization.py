from typing import List

from gatox.models.runner import Runner
from gatox.models.repository import Repository
from gatox.models.secret import Secret


class Organization:

    def __init__(self, org_data: dict, user_scopes: list, limited_data: bool = False):
        """Wrapper object for an organization."""
        self.name: str = None
        self.org_admin_user: bool = False
        self.org_admin_scopes: bool = False
        self.org_member: bool = False
        self.secrets: List[Secret] = []
        self.runners: List[Runner] = []
        self.sso_enabled: bool = False

        self.limited_data: bool = limited_data

        self.public_repos: List[Repository] = []
        self.private_repos: List[Repository] = []

        self.name = org_data['login']

        if 'billing_email' in org_data and org_data['billing_email'] is not None:
            if 'admin:org' in user_scopes:
                self.org_admin_scopes = True
            self.org_admin_user = True
            self.org_member = True
        elif 'billing_email' in org_data:
            self.org_admin_user = False
            self.org_member = True
        else:
            self.org_admin_user = False
            self.org_member = False

    def set_secrets(self, secrets: List[Secret]):
        """Set repo-level secrets."""
        self.secrets = secrets

    def set_public_repos(self, repos: List[Repository]):
        """List of public repos for the org."""
        self.public_repos = repos

    def set_private_repos(self, repos: List[Repository]):
        """List of private repos for the org."""
        self.private_repos = repos

    def set_runners(self, runners: List[Runner]):
        """Set a list of runners that the organization can access."
        self.runners = runners

    def toJSON(self):
        """Converts the repository to a Gato JSON representation."
        if self.limited_data:
            representation = {
                "name": self.name
            }
        else:
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
