import importlib
import json
import logging
import os
import shutil
import time
from datetime import datetime
from typing import List

from camel.agents import RolePlaying
from camel.configs import ChatGPTConfig
from camel.typing import ModelType, TaskType
from chatdev.chat_env import ChatEnv, ChatEnvConfig
from chatdev.statistics import get_info
from chatdev.test_suite import TestCase, TestSuite
from chatdev.utils import log_online, now


def check_bool(s):
    return s.lower() == "true"


class ChatChain:

    def __init__(self,
                 config_path: str = None,
                 config_phase_path: str = None,
                 config_role_path: str = None,
                 d4j_version: str = None,
                 project_name: str = None,
                 bug_ID: int = None,
                 test_suite: TestSuite = None,
                 test_cases: List[TestCase] = None,
                 model_type: ModelType = ModelType.GPT_3_5_TURBO,
                 project_path: str = "DebugResult",
                 cache_dir: str = "cache") -> None:
        """

        Args:
            config_path: path to the ChatChainConfig.json
            config_phase_path: path to the PhaseConfig.json
            config_role_path: path to the RoleConfig.json
            task_prompt: the user input prompt for software
            project_name: the user input name for software
            bug_ID: the defects4j bug ID
            test_suite: the failed test suite
            org_name: the organization name of the human user
        """

        # load config file
        self.config_path = config_path
        self.config_name = config_path.split("/")[-2]
        self.config_phase_path = config_phase_path
        self.config_role_path = config_role_path
        self.d4j_version = d4j_version
        self.project_name = project_name
        self.bug_ID = bug_ID
        self.test_suite = test_suite
        self.test_cases = test_cases
        self.model_type = model_type

        with open(self.config_path, 'r', encoding="utf8") as file:
            self.config = json.load(file)
        with open(self.config_phase_path, 'r', encoding="utf8") as file:
            self.config_phase = json.load(file)
        with open(self.config_role_path, 'r', encoding="utf8") as file:
            self.config_role = json.load(file)

        # init chatchain config and recruitments
        self.chain = self.config["chain"]
        self.recruitments = self.config["recruitments"]

        # init default max chat turn
        self.chat_turn_limit_default = 10

        # init ChatEnv
        self.chat_env_config = ChatEnvConfig(config_name=self.config_name,
                                             clear_structure=check_bool(self.config["clear_structure"]),
                                             brainstorming=check_bool(self.config["brainstorming"]),
                                             gui_design=check_bool(self.config["gui_design"]),
                                             git_management=check_bool(self.config["git_management"]),
                                             num_test_cases=self.config["num_test_cases"],
                                             num_test_suites=self.config["num_test_suites"],
                                             num_classes=self.config["num_classes"],
                                             test_output_tokens=self.config["test_output_tokens"],
                                             class_doc_tokens=self.config["class_doc_tokens"],
                                             method_doc_tokens=self.config["method_doc_tokens"],
                                             num_selected_classes=self.config["num_selected_classes"],
                                             basement=self.config["basement"])
        self.chat_env = ChatEnv(self.chat_env_config)

        # init role prompts
        self.role_prompts = dict()
        for role in self.config_role:
            self.role_prompts[role] = "\n".join(self.config_role[role])

        # init log
        filepath = os.path.dirname(__file__)
        root = os.path.dirname(filepath)
        self.directory = project_path
        self.cache_dir = cache_dir
        self.start_time, self.log_filepath = self.get_logfilepath()

        # init SimplePhase instances
        # import all used phases in PhaseConfig.json from chatdev.phase
        # note that in PhaseConfig.json there only exist SimplePhases
        # ComposedPhases are defined in ChatChainConfig.json and will be imported in self.execute_step
        self.compose_phase_module = importlib.import_module("chatdev.composed_phase")
        self.phase_module = importlib.import_module("chatdev.phase")
        self.phases = dict()
        for phase in self.config_phase:
            assistant_role_name = self.config_phase[phase]['assistant_role_name']
            user_role_name = self.config_phase[phase]['user_role_name']
            phase_prompt = "\n\n".join(self.config_phase[phase]['phase_prompt'])
            phase_class = getattr(self.phase_module, phase)
            phase_instance = phase_class(assistant_role_name=assistant_role_name,
                                         user_role_name=user_role_name,
                                         phase_prompt=phase_prompt,
                                         role_prompts=self.role_prompts,
                                         phase_name=phase,
                                         model_type=self.model_type,
                                         log_filepath=self.log_filepath)
            self.phases[phase] = phase_instance



    def make_recruitment(self):
        """
        recruit all employees
        Returns: None

        """
        for employee in self.recruitments:
            self.chat_env.recruit(agent_name=employee)

    def execute_step(self, phase_item: dict):
        """
        execute single phase in the chain
        Args:
            phase_item: single phase configuration in the ChatChainConfig.json

        Returns:

        """

        phase = phase_item['phase']
        phase_type = phase_item['phaseType']
        # For SimplePhase, just look it up from self.phases and conduct the "Phase.execute" method
        if phase_type == "SimplePhase":
            max_turn_step = phase_item['max_turn_step']
            need_reflect = check_bool(phase_item['need_reflect'])
            if phase in self.phases:
                self.chat_env = self.phases[phase].execute(self.chat_env,
                                                           self.chat_turn_limit_default if max_turn_step <= 0 else max_turn_step,
                                                           need_reflect)
            else:
                raise RuntimeError(f"Phase '{phase}' is not yet implemented in chatdev.phase")
        # For ComposedPhase, we create instance here then conduct the "ComposedPhase.execute" method
        elif phase_type == "ComposedPhase":
            cycle_num = phase_item['cycleNum']
            composition = phase_item['Composition']
            compose_phase_class = getattr(self.compose_phase_module, phase)
            if not compose_phase_class:
                raise RuntimeError(f"Phase '{phase}' is not yet implemented in chatdev.compose_phase")
            compose_phase_instance = compose_phase_class(phase_name=phase,
                                                         cycle_num=cycle_num,
                                                         composition=composition,
                                                         config_phase=self.config_phase,
                                                         config_role=self.config_role,
                                                         model_type=self.model_type,
                                                         log_filepath=self.log_filepath)
            self.chat_env = compose_phase_instance.execute(self.chat_env)
        else:
            raise RuntimeError(f"PhaseType '{phase_type}' is not yet implemented.")

    def execute_chain(self):
        """
        execute the whole chain based on ChatChainConfig.json
        Returns: None

        """
        for phase_item in self.chain:
            self.execute_step(phase_item)


    def get_logfilepath(self):
        """
        get the log path (under the software path)
        Returns:
            start_time: time for starting making the software
            log_filepath: path to the log

        """
        start_time = now()
        log_dir = os.path.join(self.directory, "log")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_filepath = os.path.join(log_dir, "{}.log".format("_".join([self.project_name, str(self.bug_ID), start_time])))
        return start_time, log_filepath

    def pre_processing(self):
        """
        remove useless files and log some global config settings
        Returns: None

        """
        self.chat_env.reset_dict()
        debug_path = self.directory
        self.chat_env.set_directory(debug_path)

        preprocess_msg = "**[Preprocessing]**\n\n"
        chat_gpt_config = ChatGPTConfig()

        preprocess_msg += "**ChatDev Starts** ({})\n\n".format(self.start_time)
        preprocess_msg += "**Timestamp**: {}\n\n".format(self.start_time)
        preprocess_msg += "**config_path**: {}\n\n".format(self.config_path)
        preprocess_msg += "**config_phase_path**: {}\n\n".format(self.config_phase_path)
        preprocess_msg += "**config_role_path**: {}\n\n".format(self.config_role_path)
        preprocess_msg += "**d4j_version**: {}\n\n".format(self.d4j_version)
        preprocess_msg += "**project_name**: {}\n\n".format(self.project_name)
        preprocess_msg += "**bug_ID**: {}\n\n".format(self.bug_ID)
        preprocess_msg += "**test_suite**: {}\n\n".format(str(self.test_suite.name))
        preprocess_msg += "**Log File**: {}\n\n".format(self.log_filepath)
        preprocess_msg += "**ChatDevConfig**:\n {}\n\n".format(self.chat_env.config.__str__())
        preprocess_msg += "**ChatGPTConfig**:\n {}\n\n".format(chat_gpt_config)
        log_online(preprocess_msg)

        # init bug info
        self.chat_env.env_dict['d4j_version'] = self.d4j_version
        self.chat_env.env_dict['project_name'] = self.project_name
        self.chat_env.env_dict['bug_ID'] = self.bug_ID
        self.chat_env.env_dict['cache_dir'] = self.cache_dir
        self.chat_env.test_suite = self.test_suite
        self.chat_env.test_cases = self.test_cases

    def post_processing(self):
        """
        summarize the production and move log files to the software directory
        Returns: None

        """

        
        directory = self.chat_env.env_dict['directory']
        
        self.chat_env.write_result()

        post_info = "**[Post Info]**\n\n"
        now_time = now()
        time_format = "%Y%m%d%H%M%S"
        datetime1 = datetime.strptime(self.start_time, time_format)
        datetime2 = datetime.strptime(now_time, time_format)
        duration = (datetime2 - datetime1).total_seconds()

        post_info += "Software Info: {}".format(
            get_info(directory, self.log_filepath) + "\n\n**duration**={:.2f}s\n\n".format(duration))

        post_info += "DebugDev Starts ({})".format(self.start_time) + "\n\n"
        post_info += "DebugDev Ends ({})".format(now_time) + "\n\n"

        log_online(post_info)
        with open(os.path.join(directory, f"post_info_{self.start_time}.txt"), "w", encoding="utf8") as file:
            file.write(post_info)
        
        # remove checkout directory
        buggy_path = os.path.join(directory, "buggy")
        fixed_path = os.path.join(directory, "fixed")
        os.system(f"rm -rf {buggy_path}")
        os.system(f"rm -rf {fixed_path}")

        logging.shutdown()
        time.sleep(1)

    # @staticmethod
    def self_task_improve(self, task_prompt):
        """
        ask agent to improve the user query prompt
        Args:
            task_prompt: original user query prompt

        Returns:
            revised_task_prompt: revised prompt from the prompt engineer agent

        """
        self_task_improve_prompt = """I will give you a short description of a software design requirement, 
please rewrite it into a detailed prompt that can make large language model know how to make this software better based this prompt,
the prompt should ensure LLMs build a software that can be run correctly, which is the most import part you need to consider.
remember that the revised prompt should not contain more than 200 words, 
here is the short description:\"{}\". 
If the revised prompt is revised_version_of_the_description, 
then you should return a message in a format like \"<INFO> revised_version_of_the_description\", do not return messages in other formats.""".format(
            task_prompt)
        role_play_session = RolePlaying(
            assistant_role_name="Prompt Engineer",
            assistant_role_prompt="You are an professional prompt engineer that can improve user input prompt to make LLM better understand these prompts.",
            user_role_prompt="You are an user that want to use LLM to build software.",
            user_role_name="User",
            task_type=TaskType.CHATDEV,
            task_prompt="Do prompt engineering on user query",
            with_task_specify=False,
            model_type=self.model_type,
        )

        # log_online("System", role_play_session.assistant_sys_msg)
        # log_online("System", role_play_session.user_sys_msg)

        _, input_user_msg = role_play_session.init_chat(None, None, self_task_improve_prompt)
        assistant_response, user_response = role_play_session.step(input_user_msg, True)
        revised_task_prompt = assistant_response.msg.content.split("<INFO>")[-1].lower().strip()
        log_online(role_play_session.assistant_agent.role_name, assistant_response.msg.content)
        log_online(
            "**[Task Prompt Self Improvement]**\n**Original Task Prompt**: {}\n**Improved Task Prompt**: {}".format(
                task_prompt, revised_task_prompt))
        return revised_task_prompt
