from gatox.workflow_graph.graph.tagged_graph import TaggedGraph
from gatox.workflow_graph.graph_builder import WorkflowGraphBuilder
from gatox.workflow_graph.visitors.visitor_utils import VisitorUtils
from gatox.github.api import Api
from gatox.workflow_parser.utility import CONTEXT_REGEX


class DispatchTOCTOUVisitor:
    """This class implements a graph visitor tasked with identifying
    injection issues from workflows.
    """

    @staticmethod
    def find_dispatch_misconfigurations(graph: TaggedGraph, api: Api):
        """ """

        # Now we have all reponodes
        nodes = graph.get_nodes_for_tags(
            [
                "workflow_dispatch",
            ]
        )

        all_paths = []
        results = {}

        for cn in nodes:
            paths = graph.dfs_to_tag(cn, "checkout", api)
            if paths:
                all_paths.append(paths)

        for path_set in all_paths:
            for path in path_set:
                input_lookup = {}

                # Workflow dispatch jobs inherently
                # have an approval gate, so only
                # TOCTOU issues can be exploited.
                approval_gate = True
                env_lookup = {}
                flexible_lookup = {}

                for index, node in enumerate(path):
                    tags = node.get_tags()
                    if "JobNode" in tags:
                        if node.outputs:
                            for o_key, val in node.outputs.items():
                                if "env." in val and val not in env_lookup:
                                    for key in env_lookup.keys():
                                        if key in val:
                                            flexible_lookup[o_key] = env_lookup[key]
                    elif "WorkflowNode" in tags:
                        if index != 0 and "JobNode" in path[index - 1].get_tags():
                            # Caller job node
                            node_params = path[index - 1].params
                            # Set lookup for input params
                            input_lookup.update(node_params)
                        if index == 0:
                            # If the workflow dispatch node does not have
                            # any inputs, we can skip the rest of the path.

                            if not node.inputs:
                                break

                            # Check workflow environment variables.
                            # for env vars that are github.event.*
                            env_vars = node.env_vars
                            for key, val in env_vars.items():
                                if type(val) is str:
                                    if "github." in val:
                                        env_lookup[key] = val
                    elif "StepNode" in tags:
                        if node.is_checkout:
                            checkout_ref = node.metadata
                            if "inputs." in node.metadata:
                                if "${{" in node.metadata:
                                    processed_var = CONTEXT_REGEX.findall(node.metadata)
                                    if processed_var:
                                        processed_var = processed_var[0]
                                        if "inputs." in processed_var:
                                            processed_var = processed_var.replace(
                                                "inputs.", ""
                                            )
                                    else:
                                        processed_var = node.metadata
                                else:
                                    processed_var = node.metadata

                                if processed_var in env_lookup:
                                    original_val = env_lookup[processed_var]
                                    checkout_ref = original_val
                                elif processed_var in input_lookup:
                                    checkout_ref = input_lookup[processed_var]

                            if VisitorUtils.check_mutable_ref(checkout_ref):
                                VisitorUtils._add_results(path, results)

        print("DISPATCH:")
        VisitorUtils.ascii_render(results)
