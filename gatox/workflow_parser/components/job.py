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
from gatox.configuration.configuration_manager import ConfigurationManager

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
        self.job_name = job_name
        self.job_data = job_data
        self.needs = []  # Initialize as an empty list
        self.steps = []  # Initialize as an empty list
        self.env = {}
        self.permissions = []
        self.deployments = []
        self.if_condition = None
        self.uses = None
        self.caller = False
        self.external_caller = False
        self.has_gate = False
        self.evaluated = False

        if 'environment' in self.job_data:
            if type(self.job_data['environment']) == list:
                self.deployments.extend(self.job_data['environment'])
            else:
                self.deployments.append(self.job_data['environment'])

        if 'env' in self.job_data:
            self.env = self.job_data['env']

        if 'permissions' in self.job_data:
            self.permissions = self.job_data['permissions']

        if 'if' in self.job_data:
            self.if_condition = self.job_data['if']

        if 'needs' in self.job_data:
            self.needs = self.job_data['needs']

        if 'uses' in self.job_data:
            if self.job_data['uses'].startswith('./'):
                self.uses = self.job_data['uses']
                self.caller = True
            else:     
                self.uses = self.job_data['uses']
                self.external_caller = True

        if 'steps' in self.job_data:
            for step in self.job_data['steps']:
                added_step = Step(step)
                self.steps.append(added_step)
                if added_step.is_gate:
                    self.has_gate = True

    def evaluateIf(self):
        """Evaluate the If expression by parsing it into an AST
        and then evaluating it in the context of an external user
        triggering it.
        """
        if self.if_condition and not self.evaluated:
            try:
                parser = ExpressionParser(self.if_condition)
                if self.EVALUATOR.evaluate(parser.get_node()):
                    self.if_condition = f"EVALUATED: {self.if_condition}"
                else:
                    self.if_condition = f"RESTRICTED: {self.if_condition}"
                
            except ValueError as ve:
                self.if_condition = self.if_condition
            except NotImplementedError as ni:
                self.if_condition = self.if_condition
            except (SyntaxError, IndexError) as e:
                self.if_condition = self.if_condition
            finally:
                self.evaluated = True

        return self.if_condition

    def isSelfHosted(self):
        """Check if the job is configured to use a self-hosted runner.
        """
        if 'runs-on' in self.job_data:
            return self.job_data['runs-on'].lower() == 'self-hosted'
        return False

    def __process_runner(self):
        """
        Processes the runner for the job.
        """
        raise NotImplementedError("Not Implemented!")

    def __process_matrix(self):
        """
        Processes the matrix for the job.
        """
        raise NotImplementedError("Not Implemented!")

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

    def gated(self):
        """Check if the job is gated.
        """
        return self.has_gate or (self.evaluateIf() and self.evaluateIf().startswith("RESTRICTED"))


This revised code snippet addresses the feedback by initializing the `needs` attribute as an empty list, ensuring that the `steps` list is initialized before iterating, and implementing the `isSelfHosted` method to check for self-hosted runners based on the `runs-on` attribute. The private methods `__process_runner` and `__process_matrix` are included as placeholders for future functionality, and the `gated` method is added to check if the job is gated. The code is also cleaned of extraneous comments at the end of the class definition.