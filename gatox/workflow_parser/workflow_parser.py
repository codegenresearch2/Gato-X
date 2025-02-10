import logging
from pathlib import Path
import os
import re

from gatox.configuration.configuration_manager import ConfigurationManager
from gatox.workflow_parser.utility import filter_tokens, decompose_action_ref
from gatox.workflow_parser.components.job import Job
from gatox.models.workflow import Workflow

logger = logging.getLogger(__name__)

class WorkflowParser:
    """
    Parser for YML files. This class is structured to take a yaml file as input and expose methods that
    answer questions about the yaml file. This will allow for growing what kind of analytics this tool can perform
    as the project grows in capability. This class should only perform static analysis. The caller is responsible for
    performing any API queries to augment the analysis.
    """

    LARGER_RUNNER_REGEX = re.compile(r'(windows|ubuntu)-(22.04|20.04|2019-2022)-(4|8|16|32|64)core-(16|32|64|128|256)gb')
    MATRIX_KEY_REGEX = re.compile(r'{{\s*matrix\.([\w-]+)\s*}}')

    def __init__(self, workflow_wrapper: Workflow, non_default=None):
        """
        Initialize class with workflow file.

        Args:
            workflow_wrapper (Workflow): Workflow object containing yaml file read in from repository.
            non_default (str, optional): Non-default branch name. Defaults to None.
        """
        if workflow_wrapper.isInvalid():
            raise ValueError("Received invalid workflow!")

        self.parsed_yml = workflow_wrapper.parsed_yml
        if self.parsed_yml is None:
            raise ValueError("Workflow wrapper does not contain valid parsed YAML data.")

        self.jobs = []
        if 'jobs' in self.parsed_yml and self.parsed_yml['jobs'] is not None:
            self.jobs = [Job(job_data, job_name) for job_name, job_data in self.parsed_yml['jobs'].items()]

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

    def extract_referenced_actions(self):
        """
        Extracts composite actions from the workflow file.

        Returns:
            dict: Dictionary containing referenced actions.
        """
        referenced_actions = {}
        vulnerable_triggers = self.get_vulnerable_triggers()
        if not vulnerable_triggers:
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
        risky_triggers = ['pull_request_target', 'workflow_run', 'issue_comment', 'issues', 'discussion_comment', 'discussion', 'fork', 'watch']
        if alternate:
            risky_triggers = [alternate]

        if not self.parsed_yml or 'on' not in self.parsed_yml:
            return vulnerable_triggers

        triggers = self.parsed_yml['on']
        if isinstance(triggers, list):
            for trigger in triggers:
                if trigger in risky_triggers:
                    vulnerable_triggers.append(trigger)
        elif isinstance(triggers, dict):
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

    # Rest of the code remains the same