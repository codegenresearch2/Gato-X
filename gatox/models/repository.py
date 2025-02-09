import datetime
from gatox.models.runner import Runner
from gatox.models.secret import Secret


class Repository():
    """Simple wrapper class to provide accessor methods against the repository
    JSON response from GitHub.
    """

    def __init__(self, repo_data: dict):
        """Initialize wrapper class.

        Args:
            repo_data (dict): Dictionary from parsing JSON object returned from
            GitHub
        """
        self.repo_data = repo_data
        # Temporary hack until full transition to GQL
        if 'environments' not in self.repo_data:
            self.repo_data['environments'] = []

        self.name = self.repo_data['full_name']
        self.org_name = self.name.split('/')[0]
        self.secrets: list[Secret] = []
        self.org_secrets: list[Secret] = []
        self.sh_workflow_names = []
        self.enum_time = datetime.datetime.now()

        self.permission_data = self.repo_data['permissions']
        self.sh_runner_access = False
        self.accessible_runners: list[Runner] = []
        self.runners: list[Runner] = []
        self.pwn_req_risk = []
        self.injection_risk = []

    def is_admin(self) -> bool:
        """Check if the user has admin permissions for the repository.

        Returns:
            bool: True if the user has admin permissions, False otherwise.
        """
        return self.permission_data.get('admin', False)

    def is_maintainer(self) -> bool:
        """Check if the user has maintainer permissions for the repository.

        Returns:
            bool: True if the user has maintainer permissions, False otherwise.
        """
        return self.permission_data.get('maintain', False)

    def can_push(self) -> bool:
        """Check if the user can push to the repository.

        Returns:
            bool: True if the user can push, False otherwise.
        """
        return self.permission_data.get('push', False)

    def can_pull(self) -> bool:
        """Check if the user can pull from the repository.

        Returns:
            bool: True if the user can pull, False otherwise.
        """
        return self.permission_data.get('pull', False)

    def is_private(self) -> bool:
        """Check if the repository is private.

        Returns:
            bool: True if the repository is private, False otherwise.
        """
        return not self.repo_data['visibility'] == 'public'
    
    def is_archived(self) -> bool:
        """Check if the repository is archived.

        Returns:
            bool: True if the repository is archived, False otherwise.
        """
        return self.repo_data['archived']

    def is_internal(self) -> bool:
        """Check if the repository is internal.

        Returns:
            bool: True if the repository is internal, False otherwise.
        """
        return self.repo_data['visibility'] == 'internal'

    def is_public(self) -> bool:
        """Check if the repository is public.

        Returns:
            bool: True if the repository is public, False otherwise.
        """
        return self.repo_data['visibility'] == 'public'
    
    def is_fork(self) -> bool:
        """Check if the repository is a fork.

        Returns:
            bool: True if the repository is a fork, False otherwise.
        """
        return self.repo_data['fork']

    def can_fork(self) -> bool:
        """Check if the repository allows forking.

        Returns:
            bool: True if the repository allows forking, False otherwise.
        """
        return self.repo_data.get('allow_forking', False)

    def default_path(self) -> str:
        """Get the default path for the repository.

        Returns:
            str: The default path for the repository.
        """
        return f"{self.repo_data['html_url']}/blob/{self.repo_data['default_branch']}"

    def update_time(self):
        """Update the enumeration time."""
        self.enum_time = datetime.datetime.now()

    def set_pwn_request(self, pwn_request_package: dict):
        """Set a pwn request risk package.

        Args:
            pwn_request_package (dict): The package containing pwn request information.
        """
        self.pwn_req_risk.append(pwn_request_package)

    def clear_pwn_request(self, workflow_name: str):
        """Remove a pwn request entry since it's a false positive.

        Args:
            workflow_name (str): The name of the workflow whose pwn request entry should be removed.
        """
        self.pwn_req_risk = [element for element in self.pwn_req_risk if element['workflow_name'] != workflow_name]

    def has_pwn_request(self) -> bool:
        """Check if there are any pwn request risks.

        Returns:
            bool: True if there are any pwn request risks, False otherwise.
        """
        return len(self.pwn_req_risk) > 0

    def set_injection(self, injection_package: dict):
        """Set an injection risk package.

        Args:
            injection_package (dict): The package containing injection information.
        """
        self.injection_risk.append(injection_package)

    def has_injection(self) -> bool:
        """Check if there are any injection risks.

        Returns:
            bool: True if there are any injection risks, False otherwise.
        """
        return len(self.injection_risk) > 0

    def set_secrets(self, secrets: list[Secret]):
        """Sets secrets that are attached to this repository.

        Args:
            secrets (list[Secret]): List of secret wrapper objects.
        """
        self.secrets = secrets

    def set_runners(self, runners: list[Runner]):
        """Sets list of self-hosted runners attached at the repository level.

        Args:
            runners (list[Runner]): List of runner wrapper objects.
        """
        self.sh_runner_access = True
        self.runners = runners

    def add_self_hosted_workflows(self, workflows: list):
        """Add a list of workflow file names that run on self-hosted runners.

        Args:
            workflows (list): List of workflow file names.
        """
        self.sh_workflow_names.extend(workflows)

    def add_accessible_runner(self, runner: Runner):
        """Add a runner is accessible by this repo. This runner could be org
        level or repo level.

        Args:
            runner (Runner): Runner wrapper object
        """
        self.sh_runner_access = True
        self.accessible_runners.append(runner)

    def toJSON(self):
        """Converts the repository to a Gato JSON representation.

        Returns:
            dict: The JSON representation of the repository.
        """
        representation = {
            "name": self.name,
            "enum_time": self.enum_time.ctime(),
            "permissions": self.permission_data,
            "can_fork": self.can_fork(),
            "stars": self.repo_data['stargazers_count'],
            "runner_workflows": [wf for wf in self.sh_workflow_names],
            "accessible_runners": [runner.toJSON() for runner in self.accessible_runners],
            "repo_runners": [runner.toJSON() for runner in self.runners],
            "repo_secrets": [secret.toJSON() for secret in self.secrets],
            "org_secrets": [secret.toJSON() for secret in self.org_secrets],
            "pwn_request_risk": self.pwn_req_risk,
            "injection_risk": self.injection_risk
        }

        return representation