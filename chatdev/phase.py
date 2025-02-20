import os
import re
from abc import ABC, abstractmethod

from camel.agents import RolePlaying
from camel.messages import ChatMessage
from camel.typing import ModelType, TaskType
from chatdev.chat_env import ChatEnv
from chatdev.statistics import get_info
from chatdev.utils import log_arguments, log_online
from functions.func import (
    all_methods_code_prompt,
    buggy_codes_prompt,
    covered_classes_prompt,
    failed_tests_prompt,
    get_top1_prompt,
    method_code_prompt,
    methods_list_prompt,
    methods_prompt,
    test_code_prompt,
    test_infos_prompt,
    test_utility_prompt,
)


class Phase(ABC):

    def __init__(self,
                 assistant_role_name,
                 user_role_name,
                 phase_prompt,
                 role_prompts,
                 phase_name,
                 model_type,
                 log_filepath):
        """

        Args:
            assistant_role_name: who receives chat in a phase
            user_role_name: who starts the chat in a phase
            phase_prompt: prompt of this phase
            role_prompts: prompts of all roles
            phase_name: name of this phase
        """
        self.seminar_conclusion = None
        self.assistant_role_name = assistant_role_name
        self.user_role_name = user_role_name
        self.phase_prompt = phase_prompt
        self.phase_env = dict()
        self.phase_name = phase_name
        self.assistant_role_prompt = role_prompts[assistant_role_name]
        self.user_role_prompt = role_prompts[user_role_name]
        self.timeout_seconds = 1.0
        self.max_retries = 3
        self.model_type = model_type
        self.log_filepath = log_filepath

    @log_arguments
    def chatting(
            self,
            chat_env,
            assistant_role_name: str,
            user_role_name: str,
            phase_prompt: str,
            phase_name: str,
            assistant_role_prompt: str,
            user_role_prompt: str,
            task_type=TaskType.CHATDEV,
            need_reflect=False,
            model_type=ModelType.GPT_3_5_TURBO,
            placeholders=None,
            chat_turn_limit=10
    ) -> str:
        """

        Args:
            chat_env: global chatchain environment TODO: only for employee detection, can be deleted
            assistant_role_name: who receives the chat
            user_role_name: who starts the chat
            phase_prompt: prompt of the phase
            phase_name: name of the phase
            assistant_role_prompt: prompt of assistant role
            user_role_prompt: prompt of user role
            task_type: task type
            need_reflect: flag for checking reflection
            model_type: model type
            placeholders: placeholders for phase environment to generate phase prompt
            chat_turn_limit: turn limits in each chat

        Returns:

        """

        if placeholders is None:
            placeholders = {}
        assert 1 <= chat_turn_limit <= 100

        if not chat_env.exist_employee(assistant_role_name):
            raise ValueError(f"{assistant_role_name} not recruited in ChatEnv.")
        if not chat_env.exist_employee(user_role_name):
            raise ValueError(f"{user_role_name} not recruited in ChatEnv.")

        # init role play
        role_play_session = RolePlaying(
            assistant_role_name=assistant_role_name,
            user_role_name=user_role_name,
            assistant_role_prompt=assistant_role_prompt,
            user_role_prompt=user_role_prompt,
            task_type=task_type,
            model_type=model_type,
        )

        # log_online("System", role_play_session.assistant_sys_msg)
        # log_online("System", role_play_session.user_sys_msg)

        # start the chat
        _, input_user_msg = role_play_session.init_chat(None, placeholders, phase_prompt)
        seminar_conclusion = None

        # handle chats
        # the purpose of the chatting in one phase is to get a seminar conclusion
        # there are two types of conclusion
        # 1. with "<INFO>" mark
        # 1.1 get seminar conclusion flag (ChatAgent.info) from assistant or user role, which means there exist special "<INFO>" mark in the conversation
        # 1.2 add "<INFO>" to the reflected content of the chat (which may be terminated chat without "<INFO>" mark)
        # 2. without "<INFO>" mark, which means the chat is terminated or normally ended without generating a marked conclusion, and there is no need to reflect
        for i in range(chat_turn_limit):
            # start the chat, we represent the user and send msg to assistant
            # 1. so the input_user_msg should be assistant_role_prompt + phase_prompt
            # 2. then input_user_msg send to LLM and get assistant_response
            # 3. now we represent the assistant and send msg to user, so the input_assistant_msg is user_role_prompt + assistant_response
            # 4. then input_assistant_msg send to LLM and get user_response
            # all above are done in role_play_session.step, which contains two interactions with LLM
            # the first interaction is logged in role_play_session.init_chat
            assistant_response, user_response = role_play_session.step(input_user_msg, chat_turn_limit == 1)

            conversation_meta = "**" + assistant_role_name + "<->" + user_role_name + " on : " + str(
                phase_name) + ", turn " + str(i) + "**\n\n"

            # TODO: max_tokens_exceeded errors here
            if isinstance(assistant_response.msg, ChatMessage):
                # we log the second interaction here
                log_online(role_play_session.assistant_agent.role_name,
                                     conversation_meta + "[" + role_play_session.user_agent.system_message.content + "]\n\n" + assistant_response.msg.content)
                if role_play_session.assistant_agent.info:
                    seminar_conclusion = assistant_response.msg.content
                    break
                if assistant_response.terminated:
                    break

            if isinstance(user_response.msg, ChatMessage):
                # here is the result of the second interaction, which may be used to start the next chat turn
                log_online(role_play_session.user_agent.role_name,
                                     conversation_meta + "[" + role_play_session.assistant_agent.system_message.content + "]\n\n" + user_response.msg.content)
                if role_play_session.user_agent.info:
                    seminar_conclusion = user_response.msg.content
                    break
                if user_response.terminated:
                    break

            # continue the chat
            if chat_turn_limit > 1 and isinstance(user_response.msg, ChatMessage):
                input_user_msg = user_response.msg
            else:
                break

        # conduct self reflection
        if need_reflect:
            if seminar_conclusion in [None, ""]:
                seminar_conclusion = "<INFO> " + self.self_reflection(role_play_session, phase_name,
                                                                      chat_env)
            if "recruiting" in phase_name:
                if "Yes".lower() not in seminar_conclusion.lower() and "No".lower() not in seminar_conclusion.lower():
                    seminar_conclusion = "<INFO> " + self.self_reflection(role_play_session,
                                                                          phase_name,
                                                                          chat_env)
            elif seminar_conclusion in [None, ""]:
                seminar_conclusion = "<INFO> " + self.self_reflection(role_play_session, phase_name,
                                                                      chat_env)
        else:
            seminar_conclusion = assistant_response.msg.content

        log_online("**[Seminar Conclusion]**:\n\n {}".format(seminar_conclusion))
        seminar_conclusion = seminar_conclusion.split("<INFO>")[-1]
        return seminar_conclusion

    @abstractmethod
    def update_phase_env(self, chat_env):
        """
        update self.phase_env (if needed) using chat_env, then the chatting will use self.phase_env to follow the context and fill placeholders in phase prompt
        must be implemented in customized phase
        the usual format is just like:
        ```
            self.phase_env.update({key:chat_env[key]})
        ```
        Args:
            chat_env: global chat chain environment

        Returns: None

        """
        pass

    @abstractmethod
    def update_chat_env(self, chat_env) -> ChatEnv:
        """
        update chan_env based on the results of self.execute, which is self.seminar_conclusion
        must be implemented in customized phase
        the usual format is just like:
        ```
            chat_env.xxx = some_func_for_postprocess(self.seminar_conclusion)
        ```
        Args:
            chat_env:global chat chain environment

        Returns:
            chat_env: updated global chat chain environment

        """
        pass
    
    
    def save_conclusion(self, chat_env, sub_phase_name=None) -> None:
        """save the output content of current phase to the directory.
        """
        ckpt_dir = os.path.join(chat_env.env_dict['directory'], "checkpoint", chat_env.test_suite.name)
        if sub_phase_name:
            content_file = os.path.join(ckpt_dir, f"{self.phase_name}_{sub_phase_name}.txt")
        else:
            content_file = os.path.join(ckpt_dir, self.phase_name + ".txt")
        if not os.path.exists(ckpt_dir):
            os.makedirs(ckpt_dir, exist_ok=True)
        with open(content_file, "w") as f:
            f.write(self.seminar_conclusion)
    
    def load_conclusion(self, chat_env, sub_phase_name=None) -> None:
        """load the output content of current phase from the directory.
        """
        ckpt_dir = os.path.join(chat_env.env_dict['directory'], "checkpoint", chat_env.test_suite.name)
        if sub_phase_name:
            content_file = os.path.join(ckpt_dir, f"{self.phase_name}_{sub_phase_name}.txt")
        else:
            content_file = os.path.join(ckpt_dir, self.phase_name + ".txt")
        if os.path.exists(content_file):
            with open(content_file, "r") as f:
                self.seminar_conclusion = f.read()
            log_online("**[Read Checkpoint Seminar Conclusion]**:\n\n {}".format(self.seminar_conclusion))
            print(f"Load {self.phase_name} conclusion from {content_file}")
            return True
        else:
            return False


    def execute(self, chat_env, chat_turn_limit, need_reflect) -> ChatEnv:
        """
        execute the chatting in this phase
        1. receive information from environment: update the phase environment from global environment
        2. execute the chatting or load the conclusion from checkpoint
        3. change the environment: update the global environment using the conclusion
        Args:
            chat_env: global chat chain environment
            chat_turn_limit: turn limit in each chat
            need_reflect: flag for reflection

        Returns:
            chat_env: updated global chat chain environment using the conclusion from this phase execution

        """
        
        self.update_phase_env(chat_env)
        if chat_env.config.basement != "None":
            return chat_env
        
        print(f"Start {self.phase_name} Phase.")
        
        # before chatting, we check if there is a checkpoint file for this phase
        if not self.load_conclusion(chat_env):
            self.seminar_conclusion = \
                self.chatting(chat_env=chat_env,
                              need_reflect=need_reflect,
                              assistant_role_name=self.assistant_role_name,
                              user_role_name=self.user_role_name,
                              phase_prompt=self.phase_prompt,
                              phase_name=self.phase_name,
                              assistant_role_prompt=self.assistant_role_prompt,
                              user_role_prompt=self.user_role_prompt,
                              chat_turn_limit=chat_turn_limit,
                              placeholders=self.phase_env,
                              model_type=self.model_type)
            self.save_conclusion(chat_env)

        chat_env = self.update_chat_env(chat_env)
        return chat_env


class TestBehaviorAnalysis(Phase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update_phase_env(self, chat_env):
        failed_tests = failed_tests_prompt(chat_env.test_cases)
        test_codes = test_code_prompt(chat_env.test_cases, comment=True)
        test_utility_methods = test_utility_prompt(chat_env.test_cases, self.model_type, comment=True)
        self.phase_env.update({"test_suite": chat_env.test_suite.name,
                               "failed_tests": failed_tests,
                               "test_codes": test_codes,
                               "test_utility_methods": test_utility_methods})
        chat_env.env_dict['failed_tests'] = failed_tests
        chat_env.env_dict['test_codes'] = test_codes

    def update_chat_env(self, chat_env) -> ChatEnv:
        chat_env.env_dict['test_behavior'] = self.seminar_conclusion
        return chat_env


class TestFailureAnalysis(Phase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update_phase_env(self, chat_env):
        test_infos = test_infos_prompt(chat_env.test_cases,
                                       self.model_type,
                                       test_output_tokens=chat_env.config.test_output_tokens)
        self.phase_env.update({"test_suite": chat_env.test_suite.name,
                               "failed_tests": chat_env.env_dict['failed_tests'],
                               "test_infos": test_infos,
                               "test_behavior": chat_env.env_dict['test_behavior']})
        chat_env.env_dict['test_infos'] = test_infos

    def update_chat_env(self, chat_env) -> ChatEnv:
        chat_env.env_dict['test_failure_causes'] = self.seminar_conclusion
        return chat_env


class SearchSuspiciousClass(Phase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update_phase_env(self, chat_env):
        covered_classes, classes_dict = covered_classes_prompt(chat_env.env_dict['d4j_version'],
                                                               chat_env.env_dict['project_name'],
                                                               chat_env.env_dict['bug_ID'],
                                                               chat_env.env_dict['directory'],
                                                               chat_env.env_dict['cache_dir'],
                                                               chat_env.test_suite,
                                                               self.model_type,
                                                               class_doc_tokens=chat_env.config.class_doc_tokens,
                                                               basement=chat_env.config.basement)
        chat_env.env_dict['classes_dict'] = classes_dict
        
        # if no previous phases, need to initialize the following infos
        if chat_env.env_dict['failed_tests'] == "":
            chat_env.env_dict['failed_tests'] = failed_tests_prompt(chat_env.test_cases)
        if chat_env.env_dict['test_infos'] == "":
            chat_env.env_dict['test_infos'] = test_infos_prompt(chat_env.test_cases,
                                                                self.model_type,
                                                                test_output_tokens=chat_env.config.test_output_tokens)
        
        self.phase_env.update({"test_suite": chat_env.test_suite.name,
                               "failed_tests": chat_env.env_dict['failed_tests'],
                               "test_infos": chat_env.env_dict['test_infos'],
                               "test_failure_causes": chat_env.env_dict['test_failure_causes'],
                               "covered_classes": covered_classes,
                               "num_selected_classes": chat_env.config.num_selected_classes,
                               "test_behavior": chat_env.env_dict['test_behavior']})

    def update_chat_env(self, chat_env) -> ChatEnv:
        # process seminar_conclusion
        class_names = re.findall(r"(?:\w+\.)+\w+", self.seminar_conclusion)
        class_names = [c for c in class_names if c in chat_env.env_dict['classes_dict']]
        class_names = list(set(class_names))
        if len(class_names) == 0:
            print(f"Invalid Search Suspicious Class Conclusion (SearchSuspiciousClass phase). {self.seminar_conclusion}")
        chat_env.env_dict['suspicious_classes'] = class_names
        chat_env.res_dict['buggy_classes'] = class_names
        return chat_env


class MethodDocEnhancement(Phase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update_phase_env(self, chat_env, suspicious_class):
        java_class = chat_env.env_dict['classes_dict'][suspicious_class]
        methods = methods_prompt(java_class)
        self.phase_env.update({"class_name": suspicious_class,
                               "class_documentation": java_class.doc,
                               "methods": methods})

    def update_chat_env(self, chat_env, suspicious_class) -> ChatEnv:
        # process seminar_conclusion
        java_class = chat_env.env_dict['classes_dict'][suspicious_class]
        lines = self.seminar_conclusion.split("\n")
        for line in lines:
            if not line.startswith("|"):
                continue
            items = [item.strip("| ") for item in line.split(" | ") if item != ""]
            assert len(items) == 2, f"Invalid Method Doc Enhancement Conclusion (MethodDocEnhancement phase). {str(items)}"
            if items[0] in java_class.methods:
                java_class.methods[items[0]].enhanced_doc = items[1]
        return chat_env

    def execute(self, chat_env, chat_turn_limit, need_reflect) -> ChatEnv:
        if chat_env.config.basement != "None":
            return chat_env
        for suspicious_class in chat_env.env_dict['suspicious_classes']:
            print(f"Start {self.phase_name} Phase for {suspicious_class}.")
            if chat_env.env_dict['classes_dict'][suspicious_class].methods == {}:
                print(f"No methods in {suspicious_class}.")
                continue
            self.update_phase_env(chat_env, suspicious_class)
            if not self.load_conclusion(chat_env, suspicious_class):
                self.seminar_conclusion = \
                    self.chatting(chat_env=chat_env,
                                  need_reflect=need_reflect,
                                  assistant_role_name=self.assistant_role_name,
                                  user_role_name=self.user_role_name,
                                  phase_prompt=self.phase_prompt,
                                  phase_name=self.phase_name,
                                  assistant_role_prompt=self.assistant_role_prompt,
                                  user_role_prompt=self.user_role_prompt,
                                  chat_turn_limit=chat_turn_limit,
                                  placeholders=self.phase_env,
                                  model_type=self.model_type)
                self.save_conclusion(chat_env, suspicious_class)
            chat_env = self.update_chat_env(chat_env, suspicious_class)
        return chat_env


class FindRelatedMethods(Phase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update_phase_env(self, chat_env: ChatEnv, suspicious_class):
        java_class = chat_env.env_dict['classes_dict'][suspicious_class]
        use_commet = True
        if chat_env.config.config_name == "NoMethodDoc":
            use_commet = False
        methods_list = methods_list_prompt(java_class,
                                           self.model_type,
                                           method_doc_tokens=chat_env.config.method_doc_tokens,
                                           use_comment=use_commet)
        self.phase_env.update({"test_suite": chat_env.test_suite.name,
                               "failed_tests": chat_env.env_dict['failed_tests'],
                               "class_name": suspicious_class,
                               "class_documentation": java_class.doc,
                               "test_infos": chat_env.env_dict['test_infos'],
                               "test_failure_causes": chat_env.env_dict['test_failure_causes'],
                               "methods_list": methods_list,
                               "test_behavior": chat_env.env_dict['test_behavior']})

    def update_chat_env(self, chat_env, suspicious_class) -> ChatEnv:
        # process seminar_conclusion
        java_class = chat_env.env_dict['classes_dict'][suspicious_class]
        method_names = re.findall(r"((?:\w+\.)+[\w\$]+::.+?\(.*?\))", self.seminar_conclusion)
        method_names = [m.replace(' ', '') for m in method_names]
        # filter out methods not in this suspicious class
        src_ids = [java_class.methods[m].src_id for m in java_class.methods]
        method_names = [m for m in method_names if m in src_ids]
        method_names = list(set(method_names))
        if len(method_names) == 0:
            print(f"No Related Methods Finded in Conclusion (FindRelatedMethods phase): {self.seminar_conclusion}")
        chat_env.env_dict['suspicious_methods'][suspicious_class] = method_names
        return chat_env

    def execute(self, chat_env, chat_turn_limit, need_reflect) -> ChatEnv:
        if chat_env.config.basement != "None":
            return chat_env
        for suspicious_class in chat_env.env_dict['suspicious_classes']:
            print(f"Start {self.phase_name} Phase for {suspicious_class}.")
            if chat_env.env_dict['classes_dict'][suspicious_class].methods == {}:
                print(f"No methods in {suspicious_class}.")
                continue
            self.update_phase_env(chat_env, suspicious_class)
            if not self.load_conclusion(chat_env, suspicious_class):
                self.seminar_conclusion = \
                    self.chatting(chat_env=chat_env,
                                  need_reflect=need_reflect,
                                  assistant_role_name=self.assistant_role_name,
                                  user_role_name=self.user_role_name,
                                  phase_prompt=self.phase_prompt,
                                  phase_name=self.phase_name,
                                  assistant_role_prompt=self.assistant_role_prompt, 
                                  user_role_prompt=self.user_role_prompt,
                                  chat_turn_limit=chat_turn_limit,
                                  placeholders=self.phase_env,
                                  model_type=self.model_type)
                self.save_conclusion(chat_env, suspicious_class)
            chat_env = self.update_chat_env(chat_env, suspicious_class)
        return chat_env


class MethodReview(Phase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def update_chat_env_basement(self, chat_env) -> ChatEnv:
        if chat_env.config.basement != "None":
            for suspicious_class in chat_env.env_dict['classes_dict']:
                methods = chat_env.env_dict['classes_dict'][suspicious_class].methods
                chat_env.env_dict['suspicious_methods'][suspicious_class] = [methods[m].src_id for m in methods]

    def update_phase_env(self, chat_env, spc_class, spc_method):
        java_class = chat_env.env_dict['classes_dict'][spc_class]
        method_code, method_doc = method_code_prompt(java_class, spc_method)
        self.phase_env.update({"test_suite": chat_env.test_suite.name,
                               "failed_tests": chat_env.env_dict['failed_tests'],
                               "method_name": spc_method,
                               "method_code": method_code,
                               "method_doc": method_doc,
                               "test_infos": chat_env.env_dict['test_infos'],
                               "test_failure_causes": chat_env.env_dict['test_failure_causes'],
                               "class_name": spc_class,
                               "class_doc": java_class.doc,
                               "test_behavior": chat_env.env_dict['test_behavior']})
    
    def update_phase_env_multi(self, chat_env, items):
        all_methods_text = all_methods_code_prompt(chat_env, items)
        self.phase_env.update({"test_suite": chat_env.test_suite.name,
                               "failed_tests": chat_env.env_dict['failed_tests'],
                               "method_name": None,
                               "method_code": None,
                               "method_doc": None,
                               "test_infos": chat_env.env_dict['test_infos'],
                               "test_failure_causes": chat_env.env_dict['test_failure_causes'],
                               "class_name": None,
                               "class_doc": None,
                               "all_methods": all_methods_text,
                               "test_behavior": chat_env.env_dict['test_behavior']})

    def update_chat_env(self, chat_env) -> ChatEnv:
        # process seminar_conclusion
        conclusion = self.seminar_conclusion.strip('"')
        try:
            score = re.findall(r"#(\d+)#", conclusion)[0]
            score = int(score)
        except Exception:
            raise ValueError(f"Invalid Method Review Conclusion (MethodReview phase). {conclusion}")
        
        method_name = self.phase_env['method_name']
        buggy_method = {
            "method_name": method_name,
            "method_code": self.phase_env['method_code'],
            "method_doc": self.phase_env['method_doc'],
            "class_name": self.phase_env['class_name'],
            "class_doc": self.phase_env['class_doc'],
            "test_failure_causes": self.phase_env['test_failure_causes'],
            "test_suite": self.phase_env['test_suite'],
            "score": score,
            "reason": conclusion,
        }
        buggy_code = {
            "method_name": method_name,
            "method_code": self.phase_env['method_code'],
            "method_doc": self.phase_env['method_doc'],
        }
        if method_name not in chat_env.res_dict['buggy_codes']:
            chat_env.res_dict['buggy_codes'][method_name] = buggy_code
            chat_env.res_dict['buggy_methods'].append(buggy_method)
        else:
            # we keep the highest score as the final score
            for old_buggy_method in chat_env.res_dict['buggy_methods']:
                if old_buggy_method['method_name'] == method_name:
                    old_score = old_buggy_method['score']
                    if score > old_score:
                        old_buggy_method['score'] = score
                    break
        return chat_env
    
    def update_chat_env_multi(self, chat_env) -> ChatEnv:
        suspicious_methods = chat_env.env_dict['suspicious_methods']
        all_method_names = [n for k in suspicious_methods for n in suspicious_methods[k]]

        # process seminar_conclusion
        lines = self.seminar_conclusion.split("\n")
        for line in lines:
            if not line.startswith("|"):
                continue
            items = [item.strip("| ") for item in line.split(" | ") if item != ""]
            if items[0] not in all_method_names:
                continue
            assert len(items) == 3, f"Invalid Method Review Conclusion line (MethodReview phase):{str(items)}"
            method_name, reason, score = items
            score = int(score)
            buggy_method = {
                "method_name": method_name,
                "score": score,
                "reason": reason,
            }
            buggy_code = {
                "method_name": method_name,
            }
            if method_name not in chat_env.res_dict['buggy_codes']:
                chat_env.res_dict['buggy_codes'][method_name] = buggy_code
                chat_env.res_dict['buggy_methods'].append(buggy_method)
            else:
                # we keep the highest score as the final score
                for old_buggy_method in chat_env.res_dict['buggy_methods']:
                    if old_buggy_method['method_name'] == method_name:
                        old_score = old_buggy_method['score']
                        if score > old_score:
                            old_buggy_method['score'] = score
                        break
        return chat_env

    def execute(self, chat_env: ChatEnv, chat_turn_limit, need_reflect) -> ChatEnv:
        if chat_env.config.basement != "None":
            if chat_env.env_dict['classes_dict'] == {}:
                print("No methods to review.")
                return chat_env
            self.update_chat_env_basement(chat_env)  # use search results from basement
        if chat_env.config.config_name == "NoMultipleMethodReview":
            items = list(chat_env.env_dict['suspicious_methods'].items())
            self.update_phase_env_multi(chat_env, items)
            if not self.load_conclusion(chat_env):
                self.seminar_conclusion = \
                    self.chatting(chat_env=chat_env,
                                need_reflect=need_reflect,
                                assistant_role_name=self.assistant_role_name,
                                user_role_name=self.user_role_name,
                                phase_prompt=self.phase_prompt,
                                phase_name=self.phase_name,
                                assistant_role_prompt=self.assistant_role_prompt,
                                user_role_prompt=self.user_role_prompt,
                                chat_turn_limit=chat_turn_limit,
                                placeholders=self.phase_env,
                                model_type=self.model_type)
                self.save_conclusion(chat_env)
            chat_env = self.update_chat_env_multi(chat_env)
        else:
            for spc_class, spc_methods in chat_env.env_dict['suspicious_methods'].items():
                for spc_method in spc_methods:
                    print(f"Start {self.phase_name} Phase for {spc_method}.")
                    self.update_phase_env(chat_env, spc_class, spc_method)
                    if not self.load_conclusion(chat_env, spc_method):
                        self.seminar_conclusion = \
                            self.chatting(chat_env=chat_env,
                                        need_reflect=need_reflect,
                                        assistant_role_name=self.assistant_role_name,
                                        user_role_name=self.user_role_name,
                                        phase_prompt=self.phase_prompt,
                                        phase_name=self.phase_name,
                                        assistant_role_prompt=self.assistant_role_prompt,
                                        user_role_prompt=self.user_role_prompt,
                                        chat_turn_limit=chat_turn_limit,
                                        placeholders=self.phase_env,
                                        model_type=self.model_type)
                        self.save_conclusion(chat_env, spc_method)
                    chat_env = self.update_chat_env(chat_env)
        
        # rank methods
        if len(chat_env.res_dict['buggy_methods']) > 1:
            chat_env.res_dict['buggy_methods'] = sorted(
                chat_env.res_dict['buggy_methods'],
                key=lambda x: x['score'], reverse=True
            )
        return chat_env
