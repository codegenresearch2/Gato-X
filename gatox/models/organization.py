from gatox.models.runner import Runner
from gatox.models.repository import Repository
from gatox.models.secret import Secret

class Organization:
    """Wrapper object for an organization.

    Args:
        org_data (dict): Org data from GitHub API
        user_scopes (list): List of OAuth scopes that the PAT has
        limited_data (bool): Whether limited org_data is present (default: False)
    """

    def __init__(self, org_data: dict, user_scopes: list, limited_data: bool = False):
        self.name = org_data['login']
        self.org_admin_user = 'admin:org' in user_scopes and 'billing_email' in org_data and org_data['billing_email'] is not None
        self.org_admin_scopes = 'admin:org' in user_scopes
        self.org_member = 'billing_email' in org_data
        self.secrets: list[Secret] = []
        self.runners: list[Runner] = []
        self.sso_enabled = False
        self.limited_data = limited_data
        self.public_repos: list[Repository] = []
        self.private_repos: list[Repository] = []

    def set_secrets(self, secrets: list[Secret]):
        """Set repo-level secrets.

        Args:
            secrets (list): List of secrets at the organization level.
        """
        self.secrets = secrets

    def set_repository(self, repo: Repository):
        """Add a repository to the organization's list of repositories.

        Args:
            repo (Repository): Repository wrapper object.
        """
        if repo.is_public():
            self.public_repos.append(repo)
        else:
            self.private_repos.append(repo)

    def set_runners(self, runners: list[Runner]):
        """Set a list of runners that the organization can access.

        Args:
            runners (List[Runner]): List of runners that are attached to the organization.
        """
        self.runners = runners

    def toJSON(self):
        """Converts the repository to a Gato JSON representation.

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

        if self.limited_data:
            representation = {"name": self.name}

        return representation


In the updated code, I have added the `set_repository` method to the `Organization` class. This method takes a `Repository` object as an argument and adds it to the appropriate list (`public_repos` or `private_repos`) based on its privacy status. I have also updated the `toJSON` method to construct the JSON representation based on the `limited_data` attribute at the beginning of the method.