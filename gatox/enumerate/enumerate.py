class Enumerator:
    def __init__(self, pat, socks_proxy=None, http_proxy=None, output_yaml=None, skip_log=False, github_url=None, output_json=None):
        self.pat = pat
        self.socks_proxy = socks_proxy
        self.http_proxy = http_proxy
        self.output_yaml = output_yaml
        self.skip_log = skip_log
        self.github_url = github_url
        self.output_json = output_json

    def validate_only(self):
        pass

    def self_enumeration(self):
        pass

    def enumerate_organization(self, org):
        pass

    def enumerate_repo_only(self, repo_name, large_enum=False):
        pass

    def enumerate_repos(self, repo_names):
        pass