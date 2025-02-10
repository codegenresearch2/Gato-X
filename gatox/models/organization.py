from gatox.models.runner import Runner
from gatox.models.repository import Repository
from gatox.models.secret import Secret

class Organization():

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

        self.secrets = []
        self.runners = []
        self.sso_enabled = False

        self.public_repos = []
        self.private_repos = []

        self.permissions = self.determine_permissions(org_data)

    def determine_permissions(self, org_data):
        """Determine the user's permissions within the organization.

        Args:
            org_data (dict): Org data from GitHub API

        Returns:
            dict: Dictionary containing the user's permissions
        """
        permissions = {
            "org_admin_user": False,
            "org_admin_scopes": False,
            "org_member": False
        }

        if "billing_email" in org_data and org_data["billing_email"] is not None:
            permissions["org_admin_user"] = True
            permissions["org_member"] = True
            if "admin:org" in self.user_scopes:
                permissions["org_admin_scopes"] = True
        elif "billing_email" in org_data:
            permissions["org_member"] = True

        return permissions

    def set_secrets(self, secrets: list[Secret]):
        """Set organization-level secrets.

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

    def set_sso_enabled(self, enabled: bool):
        """Set the SSO enabled status for the organization.

        Args:
            enabled (bool): Whether SSO is enabled or not.
        """
        self.sso_enabled = enabled

    def set_forking_options(self, allow_forking: bool, allow_forking_for_private_repos: bool):
        """Set the forking options for the organization.

        Args:
            allow_forking (bool): Whether forking is allowed or not.
            allow_forking_for_private_repos (bool): Whether forking is allowed for private repos or not.
        """
        self.allow_forking = allow_forking
        self.allow_forking_for_private_repos = allow_forking_for_private_repos

    def toJSON(self):
        """Converts the organization to a Gato JSON representation.
        """
        if self.limited_data:
            representation = {
                "name": self.name
            }
        else:
            representation = {
                "name": self.name,
                "permissions": self.permissions,
                "org_secrets": [secret.toJSON() for secret in self.secrets],
                "org_runners": [runner.toJSON() for runner in self.runners],
                "sso_enabled": self.sso_enabled,
                "public_repos": [repository.toJSON() for repository in self.public_repos],
                "private_repos": [repository.toJSON() for repository in self.private_repos],
                "allow_forking": self.allow_forking,
                "allow_forking_for_private_repos": self.allow_forking_for_private_repos
            }

        return representation


In the rewritten code, I have added the following changes to enhance repository management functionality, improve permission handling for repositories, and expand the data model with forking options:

1. Added a `determine_permissions` method to determine the user's permissions within the organization based on the provided `org_data` and `user_scopes`.
2. Added a `set_sso_enabled` method to set the SSO enabled status for the organization.
3. Added a `set_forking_options` method to set the forking options for the organization, including whether forking is allowed and whether forking is allowed for private repositories.
4. Updated the `toJSON` method to include the user's permissions, SSO enabled status, and forking options in the JSON representation of the organization.
5. Removed the `org_admin_user` and `org_member` attributes from the `__init__` method and moved them to the `determine_permissions` method.
6. Removed the `org_admin_scopes` attribute from the `__init__` method and moved it to the `determine_permissions` method.
7. Updated the `set_secrets`, `set_public_repos`, `set_private_repos`, and `set_runners` methods to set the corresponding attributes directly.
8. Updated the `toJSON` method to use the `permissions` attribute instead of `org_admin_user` and `org_member`.
9. Updated the `toJSON` method to include the `allow_forking` and `allow_forking_for_private_repos` attributes in the JSON representation of the organization.