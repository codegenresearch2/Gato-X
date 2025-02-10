from gatox.caching.cache_manager import CacheManager
from gatox.models.workflow import Workflow
from gatox.models.repository import Repository

class DataIngestor:
    @staticmethod
    def construct_workflow_cache(yml_results):
        cache = CacheManager()
        for result in yml_results:
            if not result or 'nameWithOwner' not in result:
                continue

            owner = result['nameWithOwner']
            cache.set_empty(owner)

            if result['object']:
                for yml_node in result['object']['entries']:
                    yml_name = yml_node['name']
                    if yml_name.lower().endswith(('yml', 'yaml')):
                        contents = yml_node['object']['text']
                        wf_wrapper = Workflow(owner, contents, yml_name)
                        cache.set_workflow(owner, yml_name, wf_wrapper)

            repo_data = {
                'full_name': result['nameWithOwner'],
                'html_url': result['url'],
                'visibility': 'private' if result['isPrivate'] else 'public',
                'default_branch': result['defaultBranchRef']['name'] if result['defaultBranchRef'] else 'main',
                'fork': result['isFork'],
                'stargazers_count': result['stargazers']['totalCount'],
                'pushed_at': result['pushedAt'],
                'permissions': {
                    'pull': result['viewerPermission'] in ['READ', 'TRIAGE', 'WRITE', 'MAINTAIN', 'ADMIN'],
                    'push': result['viewerPermission'] in ['WRITE', 'MAINTAIN', 'ADMIN'],
                    'admin': result['viewerPermission'] == 'ADMIN'
                },
                'archived': result['isArchived'],
                'isFork': result['isFork'],
                'environments': []
            }

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