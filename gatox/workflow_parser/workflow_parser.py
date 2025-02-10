import logging
import os
import re
from pathlib import Path

from gatox.configuration.configuration_manager import ConfigurationManager
from gatox.workflow_parser.utility import filter_tokens, decompose_action_ref
from gatox.workflow_parser.components.job import Job
from gatox.models.workflow import Workflow

logger = logging.getLogger(__name__)

class WorkflowParser:
    """Parser for YML files."""

    LARGER_RUNNER_REGEX = re.compile(r'(windows|ubuntu)-(22.04|20.04|2019-2022)-(4|8|16|32|64)core-(16|32|64|128|256)gb')
    MATRIX_KEY_REGEX = re.compile(r'{{\s*matrix\.([\w-]+)\s*}}')

    def __init__(self, workflow_wrapper: Workflow, non_default=None):
        if workflow_wrapper.isInvalid():
            raise ValueError("Received invalid workflow!")

        self.parsed_yml = workflow_wrapper.parsed_yml if workflow_wrapper.parsed_yml else {}
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
        return trigger in self.get_vulnerable_triggers()

    def output(self, dirpath: str):
        Path(os.path.join(dirpath, self.repo_name)).mkdir(parents=True, exist_ok=True)
        with open(os.path.join(dirpath, f'{self.repo_name}/{self.wf_name}'), 'w') as wf_out:
            wf_out.write(self.raw_yaml)
        return True

    def extract_referenced_actions(self):
        referenced_actions = {}
        if not self.get_vulnerable_triggers():
            return referenced_actions

        for job in self.jobs:
            for step in job.steps:
                if step.type == 'ACTION':
                    action_parts = decompose_action_ref(step.uses, step.step_data, self.repo_name)
                    if action_parts:
                        referenced_actions[step.uses] = action_parts

        return referenced_actions

    def get_vulnerable_triggers(self, alternate=False):
        vulnerable_triggers = []
        risky_triggers = ['pull_request_target', 'workflow_run', 'issue_comment', 'issues', 'discussion_comment', 'discussion', 'fork', 'watch']
        if alternate:
            risky_triggers = [alternate]

        triggers = self.parsed_yml.get('on', {})
        for trigger, trigger_conditions in triggers.items():
            if trigger in risky_triggers:
                if trigger_conditions and 'types' in trigger_conditions:
                    if 'labeled' in trigger_conditions['types'] and len(trigger_conditions['types']) == 1:
                        vulnerable_triggers.append(f"{trigger}:{trigger_conditions['types'][0]}")
                    else:
                        vulnerable_triggers.append(trigger)
                else:
                    vulnerable_triggers.append(trigger)

        return vulnerable_triggers

    def backtrack_gate(self, needs_name):
        if type(needs_name) == list:
            return any(self.backtrack_gate(need) for need in needs_name)
        else:
            for job in self.jobs:
                if job.job_name == needs_name:
                    if job.gated():
                        return True
                    else:
                        return self.backtrack_gate(job.needs)
        return False

    def analyze_checkouts(self):
        job_checkouts = {}
        for job in self.jobs:
            job_content = {"check_steps": [], "if_check": job.evaluateIf(), "confidence": "UNKNOWN", "gated": False}
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
                        elif if_check == '':
                            pass
                        step_details.append({"ref": step.metadata, "if_check": if_check, "step_name": step.name})
                elif step_details and step.is_sink:
                    job_content['confidence'] = 'HIGH' if (job_content['if_check'] and job_content['if_check'].startswith('EVALUATED')) or (bump_confidence and not job_content['if_check']) or (not job_content['if_check'] and (not step.evaluateIf() or step.evaluateIf().startswith('EVALUATED'))) else 'MEDIUM'

            job_content["check_steps"] = step_details
            job_checkouts[job.job_name] = job_content

        return job_checkouts

    def check_pwn_request(self, bypass=False):
        vulnerable_triggers = self.get_vulnerable_triggers()
        if not vulnerable_triggers and not bypass:
            return {}

        checkout_risk = {}
        candidates = {}

        checkout_info = self.analyze_checkouts()
        for job_name, job_content in checkout_info.items():
            steps_risk = job_content['check_steps']
            if steps_risk:
                candidates[job_name] = {"confidence": job_content['confidence'], "gated": job_content['gated'], "steps": steps_risk, "if_check": job_content['if_check'] if 'if_check' in job_content and job_content['if_check'] else ''}

        if candidates:
            checkout_risk['candidates'] = candidates
            checkout_risk['triggers'] = vulnerable_triggers

        return checkout_risk

    def check_rules(self, gate_rules):
        for rule in gate_rules:
            for job in self.jobs:
                for deploy_rule in job.deployments:
                    if rule in deploy_rule:
                        return False
        return True

    def check_injection(self, bypass=False):
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
                        return value and type(value) not in [int, float] and '${{' in value
                    return True

                env_sources = [self.parsed_yml, job.job_data, step.step_data]
                for env_source in env_sources:
                    if 'env' in env_source and tokens:
                        tokens = [token for token in tokens if check_token(token, env_source)]

                if tokens:
                    if job.needs and self.backtrack_gate(job.needs):
                        break

                    if job.job_name not in injection_risk:
                        injection_risk[job.job_name] = {'if_check': job.evaluateIf()}

                    injection_risk[job.job_name][step.name] = {"variables": list(set(tokens))}
                    if step.evaluateIf():
                        injection_risk[job.job_name][step.name]['if_checks'] = step.evaluateIf()

        if injection_risk:
            injection_risk['triggers'] = vulnerable_triggers

        return injection_risk

    def self_hosted(self):
        sh_jobs = []

        if not self.parsed_yml or 'jobs' not in self.parsed_yml or not self.parsed_yml['jobs']:
            return sh_jobs

        for jobname, job_details in self.parsed_yml['jobs'].items():
            if 'runs-on' in job_details:
                runs_on = job_details['runs-on']
                if 'self-hosted' in runs_on:
                    sh_jobs.append((jobname, job_details))
                elif 'matrix.' in runs_on:
                    matrix_match = self.MATRIX_KEY_REGEX.search(runs_on)
                    if matrix_match:
                        matrix_key = matrix_match.group(1)
                        matrix = job_details['strategy']['matrix']
                        os_list = [item[matrix_key] for item in matrix.get('include', []) if matrix_key in item] if 'include' in matrix else matrix.get(matrix_key, [])
                        os_list = [os for os in os_list if isinstance(os, str)]
                        if any(os not in ConfigurationManager().WORKFLOW_PARSING['GITHUB_HOSTED_LABELS'] and not self.LARGER_RUNNER_REGEX.match(os) for os in os_list):
                            sh_jobs.append((jobname, job_details))
                elif isinstance(runs_on, list):
                    if any(label not in ConfigurationManager().WORKFLOW_PARSING['GITHUB_HOSTED_LABELS'] and not self.LARGER_RUNNER_REGEX.match(label) for label in runs_on):
                        sh_jobs.append((jobname, job_details))
                elif isinstance(runs_on, str):
                    if runs_on not in ConfigurationManager().WORKFLOW_PARSING['GITHUB_HOSTED_LABELS'] and not self.LARGER_RUNNER_REGEX.match(runs_on):
                        sh_jobs.append((jobname, job_details))

        return sh_jobs