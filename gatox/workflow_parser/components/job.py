"""
Copyright 2024, Adnan Khan

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import re
from gatox.workflow_parser.components.step import Step
from gatox.workflow_parser.expression_parser import ExpressionParser
from gatox.workflow_parser.expression_evaluator import ExpressionEvaluator

class Job():
    """Wrapper class for a Github Actions workflow job.
    """
    LARGER_RUNNER_REGEX_LIST = re.compile(
        r'(windows|ubuntu)-(22.04|20.04|2019-2022)-(4|8|16|32|64)core-(16|32|64|128|256)gb'
    )
    MATRIX_KEY_EXTRACTION_REGEX = re.compile(
        r'{{\s*matrix\.([\w-]+)\s*}}'
    )

    EVALUATOR = ExpressionEvaluator()

    def __init__(self, job_data: dict, job_name: str):
        """Constructor for job wrapper.
        """
        if not isinstance(job_data, dict):
            raise ValueError("Job data must be a dictionary.")

        self.job_name = job_name
        self.job_data = job_data
        self.needs = job_data.get('needs', [])
        self.steps = []
        self.env = job_data.get('env', {})
        self.permissions = job_data.get('permissions', [])
        self.deployments = job_data.get('environment', [])
        self.if_condition = job_data.get('if')
        self.uses = job_data.get('uses')
        self.caller = self.uses and self.uses.startswith('./')
        self.external_caller = not self.caller
        self.has_gate = False
        self.evaluated = False

        if 'steps' in job_data:
            self.steps = [Step(step) for step in job_data['steps']]
            self.has_gate = any(step.is_gate for step in self.steps)

    def evaluateIf(self):
        """Evaluate the If expression by parsing it into an AST
        and then evaluating it in the context of an external user
        triggering it.
        """
        original_if_condition = self.if_condition
        if self.if_condition and not self.evaluated:
            try:
                parser = ExpressionParser(self.if_condition)
                if self.EVALUATOR.evaluate(parser.get_node()):
                    self.if_condition = f"EVALUATED: {self.if_condition}"
                else:
                    self.if_condition = f"RESTRICTED: {self.if_condition}"
            except ValueError:
                self.if_condition = original_if_condition
            except NotImplementedError:
                self.if_condition = original_if_condition
            except (SyntaxError, IndexError):
                self.if_condition = original_if_condition
            finally:
                self.evaluated = True
        return self.if_condition

    def gated(self):
        """Check if the workflow is gated.
        """
        return self.has_gate or (self.evaluateIf() and self.evaluateIf().startswith("RESTRICTED"))

    def getJobDependencies(self):
        """Returns Job objects for jobs that must complete 
        successfully before this one.
        """
        return self.needs

    def isCaller(self):
        """Returns true if the job is a caller (meaning it 
        references a reusable workflow that runs on workflow_call)
        """
        return self.caller

    def isSelfHosted(self):
        """Check if the job is configured to use self-hosted runners.
        """
        if 'runs-on' in self.job_data:
            runs_on = self.job_data['runs-on']
            if isinstance(runs_on, list):
                return any(runner.startswith('self-hosted') for runner in runs_on)
            elif isinstance(runs_on, str):
                return runs_on.startswith('self-hosted')
        return False

    def self_hosted(self):
        """Analyze if any jobs within the workflow utilize self-hosted runners.

        Returns:
           list: List of jobs within the workflow that utilize self-hosted
           runners.
        """
        sh_jobs = []

        for job in self.jobs:
            if job.isSelfHosted():
                sh_jobs.append((job.job_name, job.job_data))

        return sh_jobs