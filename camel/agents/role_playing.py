# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import copy
from typing import Dict, List, Optional, Sequence, Tuple

from camel.agents import ChatAgent, TaskPlannerAgent, TaskSpecifyAgent
from camel.agents.chat_agent import ChatAgentResponse
from camel.messages import ChatMessage, SystemMessage, UserChatMessage
from camel.typing import ModelType, PhaseType, RoleType, TaskType
from chatdev.utils import log_arguments, log_online


@log_arguments
class RolePlaying:
    """Role playing between two agents.
    """

    def __init__(
            self,
            assistant_role_name: str,
            user_role_name: str,
            assistant_role_prompt: str = "",
            user_role_prompt: str = "",
            model_type: ModelType = ModelType.GPT_3_5_TURBO,
            task_type: TaskType = TaskType.AI_SOCIETY,
            assistant_agent_kwargs: Optional[Dict] = None,
            user_agent_kwargs: Optional[Dict] = None,
            extend_sys_msg_meta_dicts: Optional[List[Dict]] = None,
    ) -> None:
        self.model_type = model_type
        self.task_type = task_type


        chatdev_prompt_template = "DebugDev is a software debug team powered by multiple intelligent agents, such as software test engineer, test code reviewer, architecture analyst, etc, with a multi-agent organizational structure and the mission of \"making the digital world bug-free\"."

        sys_msg_meta_dicts = [dict(chatdev_prompt=chatdev_prompt_template)] * 2
        if (extend_sys_msg_meta_dicts is None and self.task_type in [TaskType.AI_SOCIETY, TaskType.MISALIGNMENT,
                                                                     TaskType.CHATDEV]):
            extend_sys_msg_meta_dicts = [dict(assistant_role=assistant_role_name, user_role=user_role_name)] * 2
        if extend_sys_msg_meta_dicts is not None:
            sys_msg_meta_dicts = [{**sys_msg_meta_dict, **extend_sys_msg_meta_dict} for
                                  sys_msg_meta_dict, extend_sys_msg_meta_dict in
                                  zip(sys_msg_meta_dicts, extend_sys_msg_meta_dicts)]

        self.assistant_sys_msg = SystemMessage(role_name=assistant_role_name, role_type=RoleType.DEFAULT,
                                               meta_dict=sys_msg_meta_dicts[0],
                                               content=assistant_role_prompt.format(**sys_msg_meta_dicts[0]))
        self.user_sys_msg = SystemMessage(role_name=user_role_name, role_type=RoleType.DEFAULT,
                                          meta_dict=sys_msg_meta_dicts[1],
                                          content=user_role_prompt.format(**sys_msg_meta_dicts[1]))

        self.assistant_agent: ChatAgent = ChatAgent(self.assistant_sys_msg, model_type,
                                                    **(assistant_agent_kwargs or {}), )
        self.user_agent: ChatAgent = ChatAgent(self.user_sys_msg, model_type, **(user_agent_kwargs or {}), )

    def init_chat(self, phase_type: PhaseType = None,
                  placeholders=None, phase_prompt=None):
        r"""Initializes the chat by resetting both the assistant and user
        agents, and sending the system messages again to the agents using
        chat messages. Returns the assistant's introductory message and the
        user's response messages.

        Returns:
            A tuple containing an `AssistantChatMessage` representing the
            assistant's introductory message, and a list of `ChatMessage`s
            representing the user's response messages.
        """
        if placeholders is None:
            placeholders = {}
        self.assistant_agent.reset()
        self.user_agent.reset()

        # refactored ChatDev
        placeholders.update({"assistant_role": self.assistant_agent.role_name})
        content = phase_prompt.format(**placeholders)
        user_msg = UserChatMessage(
            role_name=self.user_sys_msg.role_name,
            role="user",
            content=content
            # content here will be concatenated with assistant role prompt (because we mock user and send msg to assistant) in the ChatAgent.step
        )
        pseudo_msg = copy.deepcopy(user_msg)
        pseudo_msg.role = "assistant"
        self.user_agent.update_messages(pseudo_msg)

        # here we concatenate to store the real message in the log
        log_online(self.user_agent.role_name,
                             "**[Start Chat]**\n\n[" + self.assistant_agent.system_message.content + "]\n\n" + content)
        return None, user_msg

    def process_messages(
            self,
            messages: Sequence[ChatMessage],
    ) -> ChatMessage:
        r"""Processes a list of chat messages, returning the processed message.
        If multiple messages are provided and `with_critic_in_the_loop`
        is `False`, raises a `ValueError`. If no messages are provided, also
        raises a `ValueError`.

        Args:
            messages:

        Returns:
            A single `ChatMessage` representing the processed message.
        """
        if len(messages) == 0:
            raise ValueError("No messages to process.")
        if len(messages) > 1:
            raise ValueError("Got than one message to process. "
                             f"Num of messages: {len(messages)}.")
        processed_msg = messages[0]

        return processed_msg

    def step(
            self,
            user_msg: ChatMessage,
            assistant_only: bool,
    ) -> Tuple[ChatAgentResponse, ChatAgentResponse]:
        assert isinstance(user_msg, ChatMessage), print("broken user_msg: " + str(user_msg))

        # print("assistant...")
        user_msg_rst = user_msg.set_user_role_at_backend()
        assistant_response = self.assistant_agent.step(user_msg_rst)
        if assistant_response.terminated or assistant_response.msgs is None:
            return (
                ChatAgentResponse([assistant_response.msgs], assistant_response.terminated, assistant_response.info),
                ChatAgentResponse([], False, {}))
        assistant_msg = self.process_messages(assistant_response.msgs)
        if self.assistant_agent.info:
            return (ChatAgentResponse([assistant_msg], assistant_response.terminated, assistant_response.info),
                    ChatAgentResponse([], False, {}))
        self.assistant_agent.update_messages(assistant_msg)

        if assistant_only:
            return (
                ChatAgentResponse([assistant_msg], assistant_response.terminated, assistant_response.info),
                ChatAgentResponse([], False, {})
            )

        # print("user...")
        assistant_msg_rst = assistant_msg.set_user_role_at_backend()
        user_response = self.user_agent.step(assistant_msg_rst)
        if user_response.terminated or user_response.msgs is None:
            return (ChatAgentResponse([assistant_msg], assistant_response.terminated, assistant_response.info),
                    ChatAgentResponse([user_response], user_response.terminated, user_response.info))
        user_msg = self.process_messages(user_response.msgs)
        if self.user_agent.info:
            return (ChatAgentResponse([assistant_msg], assistant_response.terminated, assistant_response.info),
                    ChatAgentResponse([user_msg], user_response.terminated, user_response.info))
        self.user_agent.update_messages(user_msg)

        return (
            ChatAgentResponse([assistant_msg], assistant_response.terminated, assistant_response.info),
            ChatAgentResponse([user_msg], user_response.terminated, user_response.info),
        )
