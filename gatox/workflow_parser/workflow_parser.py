import logging
import re
import os
from pathlib import Path

from gatox.configuration.configuration_manager import ConfigurationManager
from gatox.workflow_parser.utility import filter_tokens, decompose_action_ref
from gatox.workflow_parser.components.job import Job
from gatox.models.workflow import Workflow

logger = logging.getLogger(__name__)

class WorkflowParser():
    """Parser for YML files.

    This class is structured to take a yaml file as input, it will then
    expose methods that aim to answer questions about the yaml file.

    This will allow for growing what kind of analytics this tool can perform
    as the project grows in capability.

    This class should only perform static analysis. The caller is responsible for 
    performing any API queries to augment the analysis.
    """

    def __init__(self, workflow_wrapper: Workflow, non_default=None):
        """Initialize class with workflow file.

        Args:
            workflow_wrapper (Workflow): Workflow object containing parsed YAML data.
            non_default (str, optional): Non-default branch to analyze. Defaults to None.
        """
        if workflow_wrapper.isInvalid():
            raise ValueError("Received invalid workflow!")

        self.parsed_yml = workflow_wrapper.parsed_yml or {}
        self.jobs = [Job(job_data, job_name) for job_name, job_data in self.parsed_yml.get('jobs', {}).items()]
        self.raw_yaml = workflow_wrapper.workflow_contents
        self.repo_name = workflow_wrapper.repo_name
        self.wf_name = workflow_wrapper.workflow_name
        self.callees = []
        self.external_ref = False
       
        if workflow_wrapper.special_path:
            self.external_ref = True
            self.external_path = workflow_wrapper.special_path
            self.branch = workflow_wrapper.branch
        elif non_default:
            self.branch = non_default
        else:
            self.branch = None

        self.composites = self.extract_referenced_actions()

    def is_referenced(self):
        return self.external_ref

    def has_trigger(self, trigger):
        """Check if the workflow has a specific trigger.

        Args:
            trigger (str): The trigger to check for.
        Returns:
            bool: Whether the workflow has the specified trigger.
        """
        triggers = self.parsed_yml.get('on', {})
        if isinstance(triggers, list):
            return trigger in triggers
        elif isinstance(triggers, dict):
            return any(trigger == t for t in triggers)
        return False

    def output(self, dirpath: str):
        """Write this yaml file out to the provided directory.

        Args:
            dirpath (str): Directory to save the yaml file to.

        Returns:
            bool: Whether the file was successfully written.
        """
        Path(os.path.join(dirpath, f'{self.repo_name}')).mkdir(parents=True, exist_ok=True)

        with open(os.path.join(dirpath, f'{self.repo_name}/{self.wf_name}'), 'w') as wf_out:
            wf_out.write(self.raw_yaml)
            return True
        
    def extract_referenced_actions(self):
        """Extracts composite actions from the workflow file.
        """
        referenced_actions = {}
        for job in self.jobs:
            for step in job.steps:
                if step.type == 'ACTION':
                    action_parts = decompose_action_ref(step.uses, step.step_data, self.repo_name)
                    if action_parts:
                        referenced_actions[step.uses] = action_parts
        return referenced_actions

    def get_vulnerable_triggers(self, alternate=False):
        """Analyze if the workflow is set to execute on potentially risky triggers.

        Returns:
            list: List of triggers within the workflow that could be vulnerable
            to GitHub Actions script injection vulnerabilities.
        """
        risky_triggers = ['pull_request_target', 'workflow_run', 'issue_comment', 'issues', 'discussion_comment', 'discussion', 'fork', 'watch']
        if alternate:
            risky_triggers = [alternate]

        triggers = self.parsed_yml.get('on', {})
        vulnerable_triggers = [trigger for trigger in risky_triggers if trigger in triggers]

        return vulnerable_triggers

    def backtrack_gate(self, needs_name):
        """Attempts to find if a job needed by a specific job has a gate check.
        """
        for job in self.jobs:
            if job.job_name == needs_name and job.gated():
                return True
            elif job.job_name == needs_name and not job.gated():
                return self.backtrack_gate(job.needs)
        return False

    def analyze_checkouts(self):
        """Analyze if any steps within the workflow utilize the 'actions/checkout' action with a 'ref' parameter.

        Returns:
            job_checkouts: List of 'ref' values within the 'actions/checkout' steps.
        """
        job_checkouts = {}
        for job in self.jobs:
            job_content = {
                "check_steps": [],
                "if_check": job.evaluateIf(),
                "confidence": "UNKNOWN",
                "gated": False
            }
            step_details = []
            bump_confidence = False

            if job_content['if_check'] and job_content['if_check'].startswith("RESTRICTED"):
                job_content['gated'] = True

            for step in job.steps:
                if step.is_gate:
                    job_content['gated'] = True
                elif step.is_checkout:
                    if job_content['gated'] and ('github.event.pull_request.head.sha' in step.metadata.lower() or 'sha' in step.metadata.lower()):
                        break
                    else:
                        if_check = step.evaluateIf()   
                        if if_check and if_check.startswith('EVALUATED'):
                            bump_confidence = True
                        elif if_check and 'RESTRICTED' in if_check:
                            bump_confidence = False
                        step_details.append({"ref": step.metadata, "if_check": if_check, "step_name": step.name})

                elif step_details and step.is_sink:
                    job_content['confidence'] = 'HIGH' if (job_content['if_check'] and job_content['if_check'].startswith('EVALUATED')) or bump_confidence or (not job_content['if_check'] and (not step.evaluateIf() or step.evaluateIf().startswith('EVALUATED'))) else 'MEDIUM'

            job_content["check_steps"] = step_details
            job_checkouts[job.job_name] = job_content

        return job_checkouts

    def check_pwn_request(self, bypass=False):
        """Check for potential pwn request vulnerabilities.

        Returns:
            dict: A dictionary containing the job names as keys and a list of potentially vulnerable tokens as values.
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
                    "confidence": job_content['confidence'],
                    "gated": job_content['gated'],
                    "steps": steps_risk,
                    "if_check": job_content['if_check']
                }

        if candidates:
            checkout_risk['candidates'] = candidates
            checkout_risk['triggers'] = vulnerable_triggers

        return checkout_risk
    
    def check_rules(self, gate_rules):
        """Checks environment protection rules from the API against those specified in the job.

        Args:
            gate_rules (list): List of rules to check against.

        Returns:
            bool: Whether the job is violating any of the rules.
        """
        for rule in gate_rules:
            for job in self.jobs:
                for deploy_rule in job.deployments:
                    if rule in deploy_rule:
                        return False
        return True
            
    def check_injection(self, bypass=False):
        """Check for potential script injection vulnerabilities.

        Returns:
            dict: A dictionary containing the job names as keys and a list of potentially vulnerable tokens as values.
        """
        vulnerable_triggers = self.get_vulnerable_triggers()
        if not vulnerable_triggers and not bypass:
            return {}

        injection_risk = {}

        for job in self.jobs:
            tokens = []
            for step in job.steps:
                if step.is_gate:
                    break

                if step.is_script:
                    tokens = step.getTokens()
                    tokens = filter_tokens(tokens)
                
                def check_token(token, container):
                    if token.startswith('env.') and token.split('.')[1] in container['env']:
                        value = container['env'][token.split('.')[1]]
                        if value and '${{' in value:
                            return True
                        else:
                            return False
                    return True

                env_sources = [self.parsed_yml, job.job_data, step.step_data]
                for env_source in env_sources:
                    if 'env' in env_source and tokens:
                        tokens = [token for token in tokens if check_token(token, env_source)]
                
                if tokens:
                    if job.needs and self.backtrack_gate(job.needs):
                        break

                    if job.job_name not in injection_risk:
                        injection_risk[job.job_name] = {}
                        injection_risk[job.job_name]['if_check'] = job.evaluateIf()
   
                    injection_risk[job.job_name][step.name] = {
                        "variables": list(set(tokens))
                    }
                    if step.evaluateIf():
                        injection_risk[job.job_name][step.name]['if_checks'] = step.evaluateIf()
        if injection_risk:
            injection_risk['triggers'] = vulnerable_triggers 

        return injection_risk

    def self_hosted(self):
        """Analyze if any jobs within the workflow utilize self-hosted runners.

        Returns:
           list: List of jobs within the workflow that utilize self-hosted runners.
        """
        sh_jobs = []

        for job in self.jobs:
            if 'runs-on' in job.job_data and 'self-hosted' in job.job_data['runs-on']:
                sh_jobs.append((job.job_name, job.job_data))

        return sh_jobs