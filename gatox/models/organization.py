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

        self.org_admin_user = 'admin:org' in user_scopes
        self.org_admin_scopes = 'admin:org' in user_scopes
        self.org_member = 'billing_email' in org_data and org_data['billing_email'] is not None

        self.secrets: list[Secret] = []
        self.runners: list[Runner] = []
        self.sso_enabled = False
        self.public_repos: list[Repository] = []
        self.private_repos: list[Repository] = []

    def set_secrets(self, secrets: list[Secret]):
        """Set repo-level secrets.

        Args:
            secrets (list): List of secrets at the organization level.
        """
        self.secrets = secrets

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
        self.private_repos = repos

    def set_runners(self, runners: list[Runner]):
        """Set a list of runners that the organization can access.

        Args:
            runners (List[Runner]): List of runners that are attached to the
            organization.
        """
        self.runners = runners

    def set_repository(self, repo: Repository):
        """Add a single repository to the organization.

        Args:
            repo (Repository): Repository wrapper object.
        """
        if repo.is_private():
            self.private_repos.append(repo)
        else:
            self.public_repos.append(repo)

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

I have addressed the feedback provided by the oracle.

1. I have reviewed the logic in the `__init__` method for setting `org_admin_user`, `org_admin_scopes`, and `org_member` to match the gold code's approach.
2. I have ensured that the logic for determining whether a repository is private or public in the `set_repository` method matches the gold code's approach.
3. I have adjusted the JSON representation in the `toJSON` method to match the gold code's structure and handling of `limited_data`.
4. I have ensured that the type hinting is consistent with the gold code.

These changes should bring the code closer to the gold standard.