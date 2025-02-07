from gatox.caching.cache_manager import CacheManager\\\\\nfrom gatox.models.workflow import Workflow\\\\\nfrom gatox.models.repository import Repository\\\\\nclass DataIngestor:\\\\\n    @staticmethod\\\\\n    def construct_workflow_cache(yml_results):\\\\\n        """Creates a cache of workflow yml files retrieved from graphQL.\\\\\n        Args:\\\\\n            yml_results (list): List of results from individual GraphQL queries (100 nodes at a time).\\\\\n        """\\\\\n        cache = CacheManager()\\\\\n        for result in yml_results:\\\\\n            # Check for malformed or missing data\\\\\n            if not result or 'nameWithOwner' not in result:\\\\\n                continue\\\\\n            owner = result['nameWithOwner']\\\\\n            cache.set_empty(owner)\\\\\n            if result['object']:\\\\\n                for yml_node in result['object']['entries']:\\\\\n                    yml_name = yml_node['name']\\\\\n                    if yml_name.lower().endswith('yml') or yml_name.lower().endswith('yaml'):\\\\\n                        contents = yml_node['object']['text']\\\\\n                        wf_wrapper = Workflow(owner, contents, yml_name)\\\\\n                        cache.set_workflow(owner, yml_name, wf_wrapper)\\\\\n            repo_data = {\\\n                'full_name': result['nameWithOwner'],\\\n                'html_url': result['url'],\\\n                'visibility': 'private' if result['isPrivate'] else 'public', \\\\\n                'default_branch': result['defaultBranchRef']['name'] if result['defaultBranchRef'] else 'main', \\\\\n                'fork': result['isFork'],\\\n                'stargazers_count': result['stargazers']['totalCount'],\\\n                'pushed_at': result['pushedAt'],\\\n                'permissions': {\\\n                    'pull': result['viewerPermission'] in ['READ', 'TRIAGE', 'WRITE', 'MAINTAIN', 'ADMIN'],\\\n                    'push': result['viewerPermission'] in ['WRITE', 'MAINTAIN', 'ADMIN'],\\\n                    'admin': result['viewerPermission'] == 'ADMIN'\\\\\n                },\\\n                'archived': result['isArchived'],\\\n                'isFork': result['isFork'],\\\n                'environments': []\\\\\n            }\\\\\n            if 'environments' in result and result['environments']: \\\\\n                envs = [env['node']['name'] for env in result['environments']['edges'] if env['node']['name'] != 'github-pages']\\\\\n                repo_data['environments'] = envs\\\\\n            repo_wrapper = Repository(repo_data)\\\\\n            cache.set_repository(repo_wrapper)