from gatox.models.runner import Runner
from gatox.models.repository import Repository
from gatox.models.secret import Secret

class Organization:

    def __init__(self, org_data: dict, user_scopes: list, limited_data: bool = False):
        """Wrapper object for an organization.

        Args:
            org_data (dict): Org data from GitHub API
            user_scopes (list): List of OAuth scopes that the PAT has
            limited_data (bool): Whether limited org_data is present (default: False)
        """
        self.name = org_data['login']
        self.user_scopes = user_scopes
        self.limited_data = limited_data

        self.org_admin_user = 'admin:org' in user_scopes and 'billing_email' in org_data and org_data['billing_email'] is not None
        self.org_member = 'billing_email' in org_data

        self.secrets = []
        self.runners = []
        self.sso_enabled = False
        self.public_repos = []
        self.private_repos = []

    def set_secrets(self, secrets: list[Secret]):
        """Set repo-level secrets.

        Args:
            secrets (list): List of secrets at the organization level.
        """
        if self.org_admin_user:
            self.secrets = secrets
        else:
            raise PermissionError("User does not have permission to set organization secrets.")

    def set_public_repos(self, repos: list[Repository]):
        """List of public repos for the org.

        Args:
            repos (List[Repository]): List of Repository wrapper objects.
        """
        self.public_repos = repos

    def set_private_repos(self, repos: list[Repository]):
        """List of private repos for the org.

        Args:
            repos (List[Repository]): List of Repository wrapper objects.
        """
        if self.org_member:
            self.private_repos = repos
        else:
            raise PermissionError("User is not a member of the organization.")

    def set_runners(self, runners: list[Runner]):
        """Set a list of runners that the organization can access.

        Args:
            runners (List[Runner]): List of runners that are attached to the
            organization.
        """
        if self.org_admin_user:
            self.runners = runners
        else:
            raise PermissionError("User does not have permission to set organization runners.")

    def toJSON(self):
        """Converts the repository to a Gato JSON representation.
        """
        if self.limited_data:
            representation = {"name": self.name}
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


In this rewritten code, I have added more detailed permissions handling. The `set_secrets`, `set_private_repos`, and `set_runners` methods now raise a `PermissionError` if the user does not have the necessary permissions to perform the action. This enhances security checks and improves code readability and maintainability.