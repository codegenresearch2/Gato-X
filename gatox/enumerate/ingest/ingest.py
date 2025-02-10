from gatox.caching.cache_manager import CacheManager
from gatox.models.workflow import Workflow
from gatox.models.repository import Repository

class DataIngestor:
    @staticmethod
    def construct_workflow_cache(yml_results):
        """
        Creates a cache of workflow yml files retrieved from graphQL. Since graphql and REST do not have parity,
        we still need to use rest for most enumeration calls. This method saves off all yml files, so during org
        level enumeration if we perform yml enumeration the cached file is used instead of making github REST requests.

        Args:
            yml_results (list): List of results from individual GraphQL queries (100 nodes at a time).
        """
        cache = CacheManager()
        for result in yml_results:
            # Skip if result is missing or does not contain 'nameWithOwner'
            if not result or 'nameWithOwner' not in result:
                continue

            owner = result['nameWithOwner']
            cache.set_empty(owner)

            # If 'object' is present, iterate through its entries and cache workflow objects
            if 'object' in result and result['object']:
                for yml_node in result['object']['entries']:
                    yml_name = yml_node['name']
                    if yml_name.lower().endswith(('yml', 'yaml')):
                        contents = yml_node['object']['text']
                        wf_wrapper = Workflow(owner, contents, yml_name)
                        cache.set_workflow(owner, yml_name, wf_wrapper)

            # Construct repository data dictionary and cache the repository object
            repo_data = {
                'full_name': result['nameWithOwner'],
                'html_url': result['url'],
                'visibility': 'private' if result['isPrivate'] else 'public',
                'default_branch': result.get('defaultBranchRef', {}).get('name', 'main'),
                'fork': result['isFork'],
                'stargazers_count': result['stargazers']['totalCount'],
                'pushed_at': result['pushedAt'],
                'permissions': {
                    'pull': result['viewerPermission'] in ['READ', 'TRIAGE', 'WRITE', 'MAINTAIN', 'ADMIN'],
                    'push': result['viewerPermission'] in ['WRITE', 'MAINTAIN', 'ADMIN'],
                    'maintain': result['viewerPermission'] in ['MAINTAIN', 'ADMIN'],
                    'admin': result['viewerPermission'] == 'ADMIN'
                },
                'archived': result['isArchived'],
                'isFork': result['isFork'],
                'environments': [],
                'forking_allowed': result.get('allowForking', False)
            }

            # If 'environments' is present, capture environment names excluding 'github-pages'
            if 'environments' in result and result['environments']:
                envs = [env['node']['name'] for env in result['environments']['edges'] if env['node']['name'] != 'github-pages']
                repo_data['environments'] = envs

            repo_wrapper = Repository(repo_data)
            cache.set_repository(repo_wrapper)

        # Categorize repositories by visibility type
        private_repos = [repo for repo in cache.repositories if repo.visibility == 'private']
        public_repos = [repo for repo in cache.repositories if repo.visibility == 'public']

        # Enhance organization functionality with repository management
        organization = cache.get_organization(owner)
        if organization:
            organization.private_repos = private_repos
            organization.public_repos = public_repos