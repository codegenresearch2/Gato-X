class GqlQueries():
    """Constructs graphql queries for use with the GitHub GraphQL api.
    """

    REPO_WORKFLOWS_FRAGMENT = """
    fragment repoWorkflows on Repository {
        nameWithOwner
        stargazers {
            totalCount
        }
        isPrivate
        isArchived
        viewerPermission
        url
        isFork
        pushedAt
        defaultBranchRef {
            name
        }
        forkingAllowed
        object(expression: "HEAD:.github/workflows/") {
            ... on Tree {
                entries {
                    name
                    type
                    mode
                    object {
                        ... on Blob {
                            byteSize
                            text
                        }
                    }
                }
            }
        }
        permissions {
            pull
            push
            maintain
            admin
        }
    }
    """

    GET_YMLS = """
    query RepoFiles($node_ids: [ID!]!) {
        nodes(ids: $node_ids) {
            ... on Repository {
                ...repoWorkflows
            }
        }
    }
    """

    GET_YMLS_ENV = """
    query RepoFiles($node_ids: [ID!]!) {
        nodes(ids: $node_ids) {
            ... on Repository {
                ...repoWorkflows
                environments(first: 100) {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
        }
    }
    """

    @staticmethod
    def get_workflow_ymls_from_list(repos: list):
        """
        Constructs a list of GraphQL queries to fetch workflow YAML
        files from a list of repositories.

        This method splits the list of repositories into chunks of
        up to 100 repositories each, and constructs a separate
        GraphQL query for each chunk. Each query fetches the workflow
        YAML files from the repositories in one chunk.

        Args:
            repos (list): A list of repository slugs, where each
            slug is a string in the format "owner/name".

        Returns:
            list: A list of dictionaries, where each dictionary
            contains a single GraphQL query in the format:
            {"query": "<GraphQL query string>"}.
        """

        queries = []

        for i in range(0, len(repos), 100):
            chunk = repos[i:i + 100]
            repo_queries = []

            for j, repo in enumerate(chunk):
                owner, name = repo.split('/')
                repo_query = f"""
                repo{j + 1}: repository(owner: "{owner}", name: "{name}") {{
                    ...repoWorkflows
                }}
                """
                repo_queries.append(repo_query)

            queries.append(
                {"query": GqlQueries.REPO_WORKFLOWS_FRAGMENT + "{\n" + "\n".join(repo_queries) + "\n}"}
            )

        return queries

    @staticmethod
    def get_workflow_ymls(repos: list):
        """Retrieve workflow yml files for each repository.

        Args:
            repos (List[Repository]): List of repository objects
        Returns:
            (list): List of JSON post parameters for each graphQL query.
        """
        queries = []

        if len(repos) == 0:
            return queries

        for i in range(0, (len(repos) // 100) + 1):
            top_len = len(repos) if len(repos) < (100 + i*100) else (100 + i*100)
            query = {
                "query": GqlQueries.GET_YMLS_ENV if any(repo.permissions['push'] for repo in repos[0+100*i:top_len]) else GqlQueries.GET_YMLS,
                "variables": {
                    "node_ids": [
                        repo.repo_data['node_id'] for repo in repos[0+100*i:top_len]
                    ]
                }
            }

            queries.append(query)
        return queries