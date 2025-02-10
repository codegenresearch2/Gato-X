import logging
from pathlib import Path
import os
import re

from gatox.configuration.configuration_manager import ConfigurationManager
from gatox.workflow_parser.utility import filter_tokens, decompose_action_ref
from gatox.workflow_parser.components.job import Job
from gatox.models.workflow import Workflow

logger = logging.getLogger(__name__)

class WorkflowParser():
    """
    Parser for YML files. This class is structured to take a yaml file as input and expose methods
    that answer questions about the yaml file. This will allow for growing what kind of analytics
    this tool can perform as the project grows in capability. This class should only perform static
    analysis. The caller is responsible for performing any API queries to augment the analysis.
    """

    LARGER_RUNNER_REGEX_LIST = re.compile(r'(windows|ubuntu)-(22.04|20.04|2019-2022)-(4|8|16|32|64)core-(16|32|64|128|256)gb')
    MATRIX_KEY_EXTRACTION_REGEX = re.compile(r'{{\s*matrix\.([\w-]+)\s*}}')

    def __init__(self, workflow_wrapper: Workflow, non_default=None):
        """
        Initialize class with workflow file.

        Args:
            workflow_wrapper (Workflow): Workflow object containing yaml file read in from repository.
            non_default (str, optional): Non-default branch name. Defaults to None.

        Raises:
            ValueError: If the received workflow is invalid.
        """
        if workflow_wrapper.isInvalid():
            raise ValueError("Received invalid workflow!")

        self.parsed_yml = workflow_wrapper.parsed_yml
        self.jobs = [Job(job_data, job_name) for job_name, job_data in self.parsed_yml.get('jobs', []).items()] if 'jobs' in self.parsed_yml and self.parsed_yml['jobs'] is not None else []
        self.raw_yaml = workflow_wrapper.workflow_contents
        self.repo_name = workflow_wrapper.repo_name
        self.wf_name = workflow_wrapper.workflow_name
        self.callees = []
        self.external_ref = workflow_wrapper.special_path is not None
        self.external_path = workflow_wrapper.special_path if self.external_ref else None
        self.branch = non_default if non_default else workflow_wrapper.branch if self.external_ref else None
        self.composites = self.extract_referenced_actions()

    def is_referenced(self):
        """
        Check if the workflow is referenced externally.

        Returns:
            bool: True if the workflow is referenced externally, False otherwise.
        """
        return self.external_ref

    def has_trigger(self, trigger):
        """
        Check if the workflow has a specific trigger.

        Args:
            trigger (str): The trigger to check for.

        Returns:
            bool: True if the workflow has the specified trigger, False otherwise.
        """
        return trigger in self.get_vulnerable_triggers()

    def output(self, dirpath: str):
        """
        Write this yaml file out to the provided directory.

        Args:
            dirpath (str): Directory to save the yaml file to.

        Returns:
            bool: True if the file was successfully written, False otherwise.
        """
        Path(os.path.join(dirpath, f'{self.repo_name}')).mkdir(parents=True, exist_ok=True)
        with open(os.path.join(dirpath, f'{self.repo_name}/{self.wf_name}'), 'w') as wf_out:
            wf_out.write(self.raw_yaml)
        return True

    def extract_referenced_actions(self):
        """
        Extracts composite actions from the workflow file.

        Returns:
            dict: Dictionary containing referenced actions.
        """
        referenced_actions = {}
        vulnerable_triggers = self.get_vulnerable_triggers()
        if not vulnerable_triggers or 'jobs' not in self.parsed_yml:
            return referenced_actions

        for job in self.jobs:
            for step in job.steps:
                if step.type == 'ACTION':
                    action_parts = decompose_action_ref(step.uses, step.step_data, self.repo_name)
                    if action_parts:
                        referenced_actions[step.uses] = action_parts

        return referenced_actions

    def get_vulnerable_triggers(self, alternate=False):
        """
        Analyze if the workflow is set to execute on potentially risky triggers.

        Args:
            alternate (str, optional): Alternate trigger to check for. Defaults to False.

        Returns:
            list: List of triggers within the workflow that could be vulnerable to GitHub Actions script injection vulnerabilities.
        """
        vulnerable_triggers = []
        risky_triggers = ['pull_request_target', 'workflow_run', 'issue_comment', 'issues']
        if alternate:
            risky_triggers = [alternate]

        if not self.parsed_yml or 'on' not in self.parsed_yml:
            return vulnerable_triggers

        triggers = self.parsed_yml['on']
        if isinstance(triggers, list):
            vulnerable_triggers = [trigger for trigger in triggers if trigger in risky_triggers]
        elif isinstance(triggers, dict):
            for trigger, trigger_conditions in triggers.items():
                if trigger in risky_triggers:
                    if trigger_conditions and 'types' in trigger_conditions and 'labeled' in trigger_conditions['types'] and len(trigger_conditions['types']) == 1:
                        vulnerable_triggers.append(f"{trigger}:{trigger_conditions['types'][0]}")
                    else:
                        vulnerable_triggers.append(trigger)

        return vulnerable_triggers

    def backtrack_gate(self, needs_name):
        """
        Attempts to find if a job needed by a specific job has a gate check.

        Args:
            needs_name (str or list): The name of the job or a list of job names.

        Returns:
            bool: True if a job needed by the specified job has a gate check, False otherwise.
        """
        if type(needs_name) == list:
            return any(self.backtrack_gate(need) for need in needs_name)
        else:
            for job in self.jobs:
                if job.job_name == needs_name:
                    return job.gated() or self.backtrack_gate(job.needs)
        return False

    def analyze_checkouts(self):
        """
        Analyze if any steps within the workflow utilize the 'actions/checkout' action with a 'ref' parameter.

        Returns:
            dict: Dictionary containing information about checkout steps in each job.
        """
        job_checkouts = {}
        if 'jobs' not in self.parsed_yml:
            return job_checkouts

        for job in self.jobs:
            job_content = {
                "check_steps": [],
                "if_check": job.evaluateIf(),
                "confidence": "UNKNOWN",
                "gated": False
            }
            step_details = []
            bump_confidence = False

            if job.isCaller():
                self.callees.append(job.uses.split('/')[-1])
            elif job.external_caller:
                self.callees.append(job.uses)

            if job_content['if_check'] and job_content['if_check'].startswith("RESTRICTED"):
                job_content['gated'] = True

            for step in job.steps:
                if step.is_gate:
                    job_content['gated'] = True
                elif step.is_checkout:
                    if job.needs:
                        job_content['gated'] = self.backtrack_gate(job.needs)
                    if job_content['gated'] and ('github.event.pull_request.head.sha' in step.metadata.lower() or ('sha' in step.metadata.lower() and 'env.' in step.metadata.lower())):
                        break
                    else:
                        if_check = step.evaluateIf()
                        if if_check and if_check.startswith('EVALUATED'):
                            bump_confidence = True
                        elif if_check and 'RESTRICTED' in if_check:
                            bump_confidence = False
                        step_details.append({"ref": step.metadata, "if_check": if_check, "step_name": step.name})
                elif step_details and step.is_sink:
                    job_content['confidence'] = 'HIGH' if (job_content['if_check'] and job_content['if_check'].startswith('EVALUATED')) or (bump_confidence and not job_content['if_check']) else 'MEDIUM'

            job_content["check_steps"] = step_details
            job_checkouts[job.job_name] = job_content

        return job_checkouts

    def check_pwn_request(self, bypass=False):
        """
        Check for potential pwn request vulnerabilities.

        Args:
            bypass (bool, optional): Bypass vulnerability check. Defaults to False.

        Returns:
            dict: Dictionary containing information about potential pwn request vulnerabilities.
        """
        vulnerable_triggers = self.get_vulnerable_triggers()
        if not vulnerable_triggers and not bypass:
            return {}

        checkout_risk = {}
        candidates = {}

        checkout_info = self.analyze_checkouts()
        for job_name, job_content in checkout_info.items():
            steps_risk = job_content['check_steps']
            if steps_risk:
                candidates[job_name] = {
                    'confidence': job_content['confidence'],
                    'gated': job_content['gated'],
                    'steps': steps_risk,
                    'if_check': job_content['if_check'] if 'if_check' in job_content and job_content['if_check'] else ''
                }

        if candidates:
            checkout_risk['candidates'] = candidates
            checkout_risk['triggers'] = vulnerable_triggers

        return checkout_risk

    def check_rules(self, gate_rules):
        """
        Checks environment protection rules from the API against those specified in the job.

        Args:
            gate_rules (list): List of rules to check against.

        Returns:
            bool: True if the job is violating any of the rules, False otherwise.
        """
        for rule in gate_rules:
            for job in self.jobs:
                for deploy_rule in job.deployments:
                    if rule in deploy_rule:
                        return False
        return True

    def check_injection(self, bypass=False):
        """
        Check for potential script injection vulnerabilities.

        Args:
            bypass (bool, optional): Bypass vulnerability check. Defaults to False.

        Returns:
            dict: Dictionary containing information about potential script injection vulnerabilities.
        """
        vulnerable_triggers = self.get_vulnerable_triggers()
        if not vulnerable_triggers and not bypass:
            return {}

        injection_risk = {}

        for job in self.jobs:
            for step in job.steps:
                if step.is_gate:
                    break

                if step.is_script:
                    tokens = step.getTokens()
                else:
                    continue

                tokens = filter_tokens(tokens)

                def check_token(token, container):
                    if token.startswith('env.') and token.split('.')[1] in container['env']:
                        value = container['env'][token.split('.')[1]]
                        return not (value and type(value) not in [int, float] and '${{' in value)
                    return True

                if 'env' in self.parsed_yml and tokens:
                    tokens = [token for token in tokens if check_token(token, self.parsed_yml)]
                if 'env' in job.job_data and tokens:
                    tokens = [token for token in tokens if check_token(token, job.job_data)]
                if 'env' in step.step_data and tokens:
                    tokens = [token for token in tokens if check_token(token, step.step_data)]

                if tokens:
                    if job.needs and self.backtrack_gate(job.needs):
                        break

                    if job.job_name not in injection_risk:
                        injection_risk[job.job_name] = {'if_check': job.evaluateIf()}

                    injection_risk[job.job_name][step.name] = {
                        "variables": list(set(tokens))
                    }
                    if step.evaluateIf():
                        injection_risk[job.job_name][step.name]['if_checks'] = step.evaluateIf()

        if injection_risk:
            injection_risk['triggers'] = vulnerable_triggers

        return injection_risk

    def self_hosted(self):
        """
        Analyze if any jobs within the workflow utilize self-hosted runners.

        Returns:
            list: List of jobs within the workflow that utilize self-hosted runners.
        """
        sh_jobs = []

        if not self.parsed_yml or 'jobs' not in self.parsed_yml or not self.parsed_yml['jobs']:
            return sh_jobs

        for jobname, job_details in self.parsed_yml['jobs'].items():
            if 'runs-on' in job_details:
                runs_on = job_details['runs-on']
                if 'self-hosted' in runs_on:
                    sh_jobs.append((jobname, job_details))
                elif 'matrix.' in runs_on:
                    matrix_match = self.MATRIX_KEY_EXTRACTION_REGEX.search(runs_on)
                    if matrix_match:
                        matrix_key = matrix_match.group(1)
                    else:
                        continue

                    if 'strategy' in job_details and 'matrix' in job_details['strategy']:
                        matrix = job_details['strategy']['matrix']
                        os_list = matrix[matrix_key] if matrix_key in matrix else [inclusion[matrix_key] for inclusion in matrix['include'] if matrix_key in inclusion]

                        for key in os_list:
                            if type(key) == str and key not in ConfigurationManager().WORKFLOW_PARSING['GITHUB_HOSTED_LABELS'] and not self.LARGER_RUNNER_REGEX_LIST.match(key):
                                sh_jobs.append((jobname, job_details))
                                break
                else:
                    if type(runs_on) == list:
                        if not any(label in ConfigurationManager().WORKFLOW_PARSING['GITHUB_HOSTED_LABELS'] or self.LARGER_RUNNER_REGEX_LIST.match(label) for label in runs_on):
                            sh_jobs.append((jobname, job_details))
                    elif type(runs_on) == str and runs_on not in ConfigurationManager().WORKFLOW_PARSING['GITHUB_HOSTED_LABELS'] and not self.LARGER_RUNNER_REGEX_LIST.match(runs_on):
                        sh_jobs.append((jobname, job_details))

        return sh_jobs