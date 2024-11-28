import textwrap
from colorama import Fore, Style
from nexus_sdk import (
    create_cluster,
    create_agent_for_cluster,
    create_task,
    execute_cluster,
    get_cluster_execution_response,
)
from pysui.sui.sui_txn.sync_transaction import SuiTransaction
from pysui.sui.sui_types.scalars import ObjectID, SuiString
from pysui.sui.sui_types.collections import SuiArray

class ResearchAssistant:
    def __init__(self, client, package_id, model_id, model_owner_cap_id, paper_type, topic, length):
        """
        :param client: API client
        :param package_id: Package ID for Nexus
        :param model_id: Model ID for the agents
        :param model_owner_cap_id: Capability ID for the model owner
        :param paper_type: The type of paper being written (e.g., argumentative essay)
        :param topic: The topic of the paper
        :param length: Approximate length of the paper (e.g., 1500 words)
        """
        self.client = client
        self.package_id = package_id
        self.model_id = model_id
        self.model_owner_cap_id = model_owner_cap_id

        self.paper_type = paper_type
        self.topic = topic
        self.length = length

    def setup_cluster(self):
        cluster_id, cluster_owner_cap_id = create_cluster(
            self.client,
            self.package_id,
            "Research Assistant Cluster",
            "A cluster for assisting students and researchers in writing their course papers.",
        )
        return cluster_id, cluster_owner_cap_id

    def setup_agents(self, cluster_id, cluster_owner_cap_id):
        agent_configs = [
            (
                "topic_explorer",
                "Topic Explorer",
                "Retrieve foundational knowledge about the topic using Wikipedia.",
            ),
            (
                "paper_finder",
                "Paper Finder",
                "Find and summarize academic papers related to the topic using Arxiv.",
            ),
            (
                "writing_suggestions",
                "Writing Suggestions Generator",
                "Provide practical suggestions for structuring and writing the paper.",
            ),
        ]

        for agent_name, role, goal in agent_configs:
            create_agent_for_cluster(
                self.client,
                self.package_id,
                cluster_id,
                cluster_owner_cap_id,
                self.model_id,
                self.model_owner_cap_id,
                agent_name,
                role,
                goal,
                f"An AI agent specialized in {role.lower()} for course paper assistance.",
            )

    def setup_tasks(self, cluster_id, cluster_owner_cap_id):
        tasks = [
            (
                "explore_topic",
                "topic_explorer",
                f"""
                Use Wikipedia to retrieve and summarize detailed information about the topic.
                Topic: {self.topic}
                Provide suggestions for key concepts to cover, and significant facts.
                """,
            ),
            (
                "find_related_papers",
                "paper_finder",
                f"""
                Query Arxiv to find and summarize relevant academic papers related to the topic.
                Topic: {self.topic}
                Include titles, abstracts, and links to the papers.
                """,
            ),
            (
                "generate_writing_suggestions",
                "writing_suggestions",
                f"""
                Provide a tailored list of suggestions for writing a high-quality {self.paper_type}. Include suggestions for Topic Explorer.
                The paper should be approximately {self.length} long.
                Include recommendations for structure, and writing tips as well as links to 3 related papers for a {self.topic}.
                Topic: {self.topic}
                """,
            ),
        ]

        task_ids = []
        for task_name, agent_id, description in tasks:
            task_id = create_task(
                self.client,
                self.package_id,
                cluster_id,
                cluster_owner_cap_id,
                task_name,
                agent_id,
                description,
                f"Complete {task_name} for assisting in course paper writing",
                description,
                "",  # No specific context provided in this example
            )
            task_ids.append(task_id)

        # Attach tools to tasks
        self.attach_tools_to_tasks(cluster_id, cluster_owner_cap_id)

        return task_ids

    def attach_tools_to_tasks(self, cluster_id, cluster_owner_cap_id):
        # Attach Wikipedia tool to the "explore_topic" task
        self.attach_tool_to_task(
            cluster_id,
            cluster_owner_cap_id,
            task_name="explore_topic",
            tool_name="wikipedia",
            tool_args=[self.topic],
        )

        # Attach Arxiv tool to the "find_related_papers" task
        self.attach_tool_to_task(
            cluster_id,
            cluster_owner_cap_id,
            task_name="find_related_papers",
            tool_name="arxiv",
            tool_args=[self.topic],
        )

    def attach_tool_to_task(self, cluster_id, cluster_owner_cap_id, task_name, tool_name, tool_args):
        txn = SuiTransaction(client=self.client)

        try:
            result = txn.move_call(
                target=f"{self.package_id}::cluster::attach_tool_to_task_entry",
                arguments=[
                    ObjectID(cluster_id),
                    ObjectID(cluster_owner_cap_id),
                    SuiString(task_name),
                    SuiString(tool_name),
                    SuiArray([SuiString(arg) for arg in tool_args]),
                ],
            )
        except Exception as e:
            print(f"Error in attach_task_to_tool: {e}")
            return None

        result = txn.execute(gas_budget=10000000)

        if result.is_ok():
            if result.result_data.effects.status.status == "success":
                print(f"Tool {tool_name} attached to task {task_name}")
                return True
            else:
                error_message = result.result_data.effects.status.error
                print(f"Transaction failed: {error_message}")
                return None
        return None

    def run(self):
        cluster_id, cluster_owner_cap_id = self.setup_cluster()
        self.setup_agents(cluster_id, cluster_owner_cap_id)
        self.setup_tasks(cluster_id, cluster_owner_cap_id)

        execution_id = execute_cluster(
            self.client,
            self.package_id,
            cluster_id,
            f"""
            Assist in writing a {self.paper_type} on the topic: {self.topic}.
            The paper should be approximately {self.length} long.
        """,
        )

        if execution_id is None:
            return "Cluster execution failed"

        print(f"Cluster execution started with ID: {execution_id}")
        return get_cluster_execution_response(self.client, execution_id, 600)


# Runs the Research Assistant example using the provided Nexus package ID.
def run_research_assistant_example(client, package_id, model_id, mode_owner_cap):
    print(f"{Fore.CYAN}## Welcome to Research Assistant using Nexus{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}-------------------------------{Style.RESET_ALL}")

    paper_type = input(f"{Fore.GREEN}What type of paper are you writing (e.g., argumentative essay, research proposal, thesis, etc)? {Style.RESET_ALL}")
    topic = input(f"{Fore.GREEN}What is the topic of your paper? {Style.RESET_ALL}")
    length = input(f"{Fore.GREEN}What is the approximate length of the paper (e.g., 1500 words, 5 pages)? {Style.RESET_ALL}")

    assistant = ResearchAssistant(
        client,
        package_id,
        model_id,
        mode_owner_cap,
        paper_type,
        topic,
        length,
    )

    print()
    result = assistant.run()

    print(f"\n\n{Fore.CYAN}########################{Style.RESET_ALL}")
    print(f"{Fore.CYAN}## Here are suggestions for your paper{Style.RESET_ALL}")
    print(f"{Fore.CYAN}########################\n{Style.RESET_ALL}")

    paginate_output(result)


# Helper function to paginate the result output
def paginate_output(text, width=80):
    lines = text.split("\n")

    for i, line in enumerate(lines, 1):
        wrapped_line = textwrap.fill(line, width)
        print(wrapped_line)

        # It's nice when this equals the number of lines in the terminal, using
        # default value 32 for now.
        pause_every_n_lines = 32
        if i % pause_every_n_lines == 0:
            input(f"{Fore.YELLOW}-- Press Enter to continue --{Style.RESET_ALL}")
