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
        self.jobs = []
        if self.parsed_yml and 'jobs' in self.parsed_yml:
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

    # Rest of the code remains the same