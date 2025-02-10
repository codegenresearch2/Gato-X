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
        self.name = None
        self.org_admin_user = False
        self.org_admin_scopes = False
        self.org_member = False
        self.secrets: list[Secret] = []
        self.runners: list[Runner] = []
        self.sso_enabled = False
        self.limited_data = limited_data
        self.public_repos = []
        self.private_repos = []

        self.name = org_data['login']

        if "billing_email" in org_data:
            if org_data["billing_email"] is not None:
                self.org_member = True
                if "admin:org" in user_scopes:
                    self.org_admin_scopes = True
                    self.org_admin_user = True
            else:
                self.org_member = False
        else:
            self.org_member = False

    def set_repository(self, repo: Repository):
        """Add a single repository to the organization.

        Args:
            repo (Repository): Repository wrapper object.
        """
        if repo.is_private():
            self.private_repos.append(repo)
        else:
            self.public_repos.append(repo)

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

1. I have refined the conditions for setting `org_admin_user` and `org_member` to match the more structured approach used in the gold code.
2. I have ensured that the order of methods in the class matches the gold code exactly.
3. I have adjusted the phrasing and structure of comments to match the style of the gold code.
4. I have adjusted the formatting of the dictionary in the `toJSON` method for better readability, ensuring that line breaks and indentation are consistent with the gold code.
5. I have ensured that all attributes are initialized in a consistent order that reflects the gold code.

These changes should bring the code even closer to the gold standard.