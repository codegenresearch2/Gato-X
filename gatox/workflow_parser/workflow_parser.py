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
    Parser for YML files.

    This class is structured to take a yaml file as input and exposes methods to answer questions about the yaml file.
    This allows for growing what kind of analytics this tool can perform as the project grows in capability.

    This class should only perform static analysis. The caller is responsible for performing any API queries to augment the analysis.
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
        if self.parsed_yml is None:
            raise ValueError("Workflow content is invalid or not defined.")

        self.jobs = [Job(job_data, job_name) for job_name, job_data in self.parsed_yml.get('jobs', {}).items()]
        self.raw_yaml = workflow_wrapper.workflow_contents
        self.repo_name = workflow_wrapper.repo_name
        self.wf_name = workflow_wrapper.workflow_name
        self.callees = []
        self.external_path = workflow_wrapper.special_path
        self.branch = workflow_wrapper.branch if self.external_path else non_default
        self.composites = self.extract_referenced_actions()

    def extract_referenced_actions(self):
        """
        Extracts composite actions from the workflow file.

        Returns:
            dict: A dictionary containing the referenced actions.
        """
        referenced_actions = {}
        vulnerable_triggers = self.get_vulnerable_triggers()
        if not vulnerable_triggers:
            return referenced_actions

        if 'jobs' not in self.parsed_yml:
            return referenced_actions

        for job in self.jobs:
            for step in job.steps:
                if step.type == 'ACTION':
                    action_parts = decompose_action_ref(step.uses, step.step_data, self.repo_name)
                    if action_parts:
                        referenced_actions[step.uses] = action_parts

        return referenced_actions

    # Rest of the code...