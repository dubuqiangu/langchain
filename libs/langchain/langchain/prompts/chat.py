"""Chat prompt template."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, List, Sequence, Tuple, Type, TypeVar, Union

from pydantic import Field, root_validator
from typing import Any, Callable, List, Tuple, Type, TypeVar, Union, Sequence

from langchain.load.serializable import Serializable
from langchain.prompts.base import StringPromptTemplate
from langchain.prompts.prompt import PromptTemplate
from langchain.schema import (
    BasePromptTemplate,
    PromptValue,
)
from langchain.schema.messages import (
    AIMessage,
    BaseMessage,
    ChatMessage,
    HumanMessage,
    SystemMessage,
    get_buffer_string,
)


class BaseMessagePromptTemplate(Serializable, ABC):
    """Base class for message prompt templates."""

    @property
    def lc_serializable(self) -> bool:
        """Whether this object should be serialized.

        Returns:
            Whether this object should be serialized.
        """
        return True

    @abstractmethod
    def format_messages(self, **kwargs: Any) -> List[BaseMessage]:
        """Format messages from kwargs. Should return a list of BaseMessages.

        Args:
            **kwargs: Keyword arguments to use for formatting.

        Returns:
            List of BaseMessages.
        """

    @property
    @abstractmethod
    def input_variables(self) -> List[str]:
        """Input variables for this prompt template.

        Returns:
            List of input variables.
        """

    def __add__(self, other: Any) -> ChatPromptTemplate:
        prompt = ChatPromptTemplate(messages=[self])
        return prompt + other


class MessagesPlaceholder(BaseMessagePromptTemplate):
    """Prompt template that assumes variable is already list of messages."""

    variable_name: str
    """Name of variable to use as messages."""

    def format_messages(self, **kwargs: Any) -> List[BaseMessage]:
        """To a BaseMessage.

        Args:
            **kwargs: Keyword arguments to use for formatting.

        Returns:
            List of BaseMessage.
        """
        value = kwargs[self.variable_name]
        if not isinstance(value, list):
            raise ValueError(
                f"variable {self.variable_name} should be a list of base messages, "
                f"got {value}"
            )
        for v in value:
            if not isinstance(v, BaseMessage):
                raise ValueError(
                    f"variable {self.variable_name} should be a list of base messages,"
                    f" got {value}"
                )
        return value

    @property
    def input_variables(self) -> List[str]:
        """Input variables for this prompt template.

        Returns:
            List of input variable names.
        """
        return [self.variable_name]


MessagePromptTemplateT = TypeVar(
    "MessagePromptTemplateT", bound="BaseStringMessagePromptTemplate"
)
"""Type variable for message prompt templates."""


class BaseStringMessagePromptTemplate(BaseMessagePromptTemplate, ABC):
    """Base class for message prompt templates that use a string prompt template."""

    prompt: StringPromptTemplate
    """String prompt template."""
    additional_kwargs: dict = Field(default_factory=dict)
    """Additional keyword arguments to pass to the prompt template."""

    @classmethod
    def from_template(
        cls: Type[MessagePromptTemplateT],
        template: str,
        template_format: str = "f-string",
        **kwargs: Any,
    ) -> MessagePromptTemplateT:
        """Create a class from a string template.

        Args:
            template: a template.
            template_format: format of the template.
            **kwargs: keyword arguments to pass to the constructor.

        Returns:
            A new instance of this class.
        """
        prompt = PromptTemplate.from_template(template, template_format=template_format)
        return cls(prompt=prompt, **kwargs)

    @classmethod
    def from_template_file(
        cls: Type[MessagePromptTemplateT],
        template_file: Union[str, Path],
        input_variables: List[str],
        **kwargs: Any,
    ) -> MessagePromptTemplateT:
        """Create a class from a template file.

        Args:
            template_file: path to a template file. String or Path.
            input_variables: list of input variables.
            **kwargs: keyword arguments to pass to the constructor.

        Returns:
            A new instance of this class.
        """
        prompt = PromptTemplate.from_file(template_file, input_variables)
        return cls(prompt=prompt, **kwargs)

    @abstractmethod
    def format(self, **kwargs: Any) -> BaseMessage:
        """To a BaseMessage."""

    def format_messages(self, **kwargs: Any) -> List[BaseMessage]:
        """Format messages from kwargs. Should return a list of BaseMessages.

        Args:
            **kwargs: Keyword arguments to use for formatting.

        Returns:
            List of BaseMessages.
        """
        return [self.format(**kwargs)]

    @property
    def input_variables(self) -> List[str]:
        """
        Input variables for this prompt template.

        Returns:
            List of input variable names.
        """
        return self.prompt.input_variables


class ChatMessagePromptTemplate(BaseStringMessagePromptTemplate):
    """Chat message prompt template."""

    role: str
    """Role of the message."""

    def format(self, **kwargs: Any) -> BaseMessage:
        text = self.prompt.format(**kwargs)
        return ChatMessage(
            content=text, role=self.role, additional_kwargs=self.additional_kwargs
        )


class HumanMessagePromptTemplate(BaseStringMessagePromptTemplate):
    """Human message prompt template. This is a message that is sent to the user."""

    def format(self, **kwargs: Any) -> BaseMessage:
        text = self.prompt.format(**kwargs)
        return HumanMessage(content=text, additional_kwargs=self.additional_kwargs)


class AIMessagePromptTemplate(BaseStringMessagePromptTemplate):
    """AI message prompt template. This is a message that is not sent to the user."""

    def format(self, **kwargs: Any) -> BaseMessage:
        text = self.prompt.format(**kwargs)
        return AIMessage(content=text, additional_kwargs=self.additional_kwargs)


class SystemMessagePromptTemplate(BaseStringMessagePromptTemplate):
    """System message prompt template.
    This is a message that is not sent to the user.
    """

    def format(self, **kwargs: Any) -> BaseMessage:
        text = self.prompt.format(**kwargs)
        return SystemMessage(content=text, additional_kwargs=self.additional_kwargs)


class ChatPromptValue(PromptValue):
    """Chat prompt value.

    A type of a prompt value that is built from messages.
    """

    messages: List[BaseMessage]
    """List of messages."""

    def to_string(self) -> str:
        """Return prompt as string."""
        return get_buffer_string(self.messages)

    def to_messages(self) -> List[BaseMessage]:
        """Return prompt as a list of messages."""
        return self.messages


class BaseChatPromptTemplate(BasePromptTemplate, ABC):
    """Base class for chat prompt templates."""

    def format(self, **kwargs: Any) -> str:
        return self.format_prompt(**kwargs).to_string()

    def format_prompt(self, **kwargs: Any) -> PromptValue:
        """
        Format prompt. Should return a PromptValue.
        Args:
            **kwargs: Keyword arguments to use for formatting.

        Returns:
            PromptValue.
        """
        messages = self.format_messages(**kwargs)
        return ChatPromptValue(messages=messages)

    @abstractmethod
    def format_messages(self, **kwargs: Any) -> List[BaseMessage]:
        """Format kwargs into a list of messages."""


class ChatPromptTemplate(BaseChatPromptTemplate, ABC):
    """Use to create flexible templated prompts for chat models.

    Examples:

        .. code-block:: python

            template = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful AI bot. Your name is {name}."),
                ("human", "Hello, how are you doing?"),
                ("AI", "I'm doing well, thanks!"),
                ("human", "{user_input}"),
            ])

            messages = template.format_messages(
                name="Bob",
                user_input="What is your name?"
            )
    """

    input_variables: List[str]
    """List of input variables."""
    messages: List[Union[BaseMessagePromptTemplate, BaseMessage]]
    """List of messages consisting of either message prompt templates or messages."""

    def __add__(self, other: Any) -> ChatPromptTemplate:
        # Allow for easy combining
        if isinstance(other, ChatPromptTemplate):
            return ChatPromptTemplate(messages=self.messages + other.messages)
        elif isinstance(other, (BaseMessagePromptTemplate, BaseMessage)):
            return ChatPromptTemplate(messages=self.messages + [other])
        elif isinstance(other, str):
            prompt = HumanMessagePromptTemplate.from_template(other)
            return ChatPromptTemplate(messages=self.messages + [prompt])
        else:
            raise NotImplementedError(f"Unsupported operand type for +: {type(other)}")

    @root_validator(pre=True)
    def validate_input_variables(cls, values: dict) -> dict:
        """Validate input variables.

        If input_variables is not set, it will be set to the union of
        all input variables in the messages.

        Args:
            values: values to validate.

        Returns:
            Validated values.
        """
        messages = values["messages"]
        input_vars = set()
        for message in messages:
            if isinstance(message, BaseMessagePromptTemplate):
                input_vars.update(message.input_variables)
        if "partial_variables" in values:
            input_vars = input_vars - set(values["partial_variables"])
        if "input_variables" in values:
            if input_vars != set(values["input_variables"]):
                raise ValueError(
                    "Got mismatched input_variables. "
                    f"Expected: {input_vars}. "
                    f"Got: {values['input_variables']}"
                )
        else:
            values["input_variables"] = list(input_vars)
        return values

    @classmethod
    def from_template(cls, template: str, **kwargs: Any) -> ChatPromptTemplate:
        """Create a chat prompt template from a template string.

        Creates a chat template consisting of a single message assumed to be from
        the human.

        Args:
            template: template string
            **kwargs: keyword arguments to pass to the constructor.

        Returns:
            A new instance of this class.
        """
        prompt_template = PromptTemplate.from_template(template, **kwargs)
        message = HumanMessagePromptTemplate(prompt=prompt_template)
        return cls.from_messages([message])

    @classmethod
    def from_role_strings(
        cls, string_messages: List[Tuple[str, str]]
    ) -> ChatPromptTemplate:
        """Create a class from a list of (role, template) tuples.

        The roles "human", "ai", and "system" are special and will be converted
        to the appropriate message class. All other roles will be converted to a
        generic ChatMessagePromptTemplate.

        Args:
            string_messages: list of (role, template) tuples.

        Returns:
            a chat prompt template
        """
        return cls.from_messages(string_messages)

    @classmethod
    def from_strings(
        cls, string_messages: List[Tuple[Type[BaseMessagePromptTemplate], str]]
    ) -> ChatPromptTemplate:
        """Create a class from a list of (role class, template) tuples.

        Args:
            string_messages: list of (role class, template) tuples.

        Returns:
            a chat prompt template
        """
        return cls.from_messages(string_messages)

    @classmethod
    def from_messages(
        cls,
        messages: Sequence[
            Union[
                BaseMessagePromptTemplate,
                BaseMessage,
                Tuple[str, str],
                Tuple[Type, str],
                str,
            ]
        ],
    ) -> ChatPromptTemplate:
        """Create a chat prompt template from a variety of message formats.

        Examples:

            Instantiation from a list of role strings and templates:

            .. code-block:: python

                template = ChatPromptTemplate.from_messages([
                    ("human", "Hello, how are you?"),
                    ("AI", "I'm doing well, thanks!"),
                    ("human", "That's good to hear."),
                ])

            Instantiation from mixed message formats:

            .. code-block:: python

                template = ChatPromptTemplate.from_messages([
                    SystemMessage(content="hello"),
                    ("human", "Hello, how are you?"),
                ])

            Instantiation from a list message templates:

                template = ChatPromptTemplate.from_messages([
                    ("human", "Hello, how are you?"),
                    ("AI", "I'm doing well, thanks!"),
                    ("human", "That's good to hear."),
                ])


        Args:
            messages: sequence of message representations.
                  A message can be represented using the following formats:
                  - BaseMessagePromptTemplate
                  - BaseMessage
                  - 2-tuple of (role string, template); e.g., ("human", "{user_input}")
                  - 2-tuple of (message class, template)
                  - string: short-hand for ("human", template); e.g., "{user_input}"

        Returns:
            a chat prompt template
        """
        _messages = [_convert_to_message(message) for message in messages]

        # Automatically infer input variables from messages
        input_vars = set()
        for _message in _messages:
            if isinstance(_message, BaseMessagePromptTemplate):
                input_vars.update(_message.input_variables)

        return cls(input_variables=sorted(input_vars), messages=_messages)

    def format(self, **kwargs: Any) -> str:
        """Format the chat template into a string.

        Args:
            **kwargs: keyword arguments to use for filling in template variables
                      in all the template messages in this chat template.

        Returns:
            formatted string
        """
        return self.format_prompt(**kwargs).to_string()

    def format_messages(self, **kwargs: Any) -> List[BaseMessage]:
        """Format the chat template into a list of finalized messages.

        Args:
            **kwargs: keyword arguments to use for filling in template variables
                      in all the template messages in this chat template.

        Returns:
            list of formatted messages
        """
        kwargs = self._merge_partial_and_user_variables(**kwargs)
        result = []
        for message_template in self.messages:
            if isinstance(message_template, BaseMessage):
                result.extend([message_template])
            elif isinstance(message_template, BaseMessagePromptTemplate):
                rel_params = {
                    k: v
                    for k, v in kwargs.items()
                    if k in message_template.input_variables
                }
                message = message_template.format_messages(**rel_params)
                result.extend(message)
            else:
                raise ValueError(f"Unexpected input: {message_template}")
        return result

    def partial(self, **kwargs: Union[str, Callable[[], str]]) -> BasePromptTemplate:
        raise NotImplementedError

    @property
    def _prompt_type(self) -> str:
        """Name of prompt type."""
        return "chat"

    def save(self, file_path: Union[Path, str]) -> None:
        """Save prompt to file.

        Args:
            file_path: path to file.
        """
        raise NotImplementedError()


def _create_template_from_role_string(
    role: str, template: str
) -> BaseMessagePromptTemplate:
    """Create a message prompt template from a role string and template."""
    if role == "human":
        message = HumanMessagePromptTemplate.from_template(template)
    elif role == "ai":
        message = AIMessagePromptTemplate.from_template(template)
    elif role == "system":
        message = SystemMessagePromptTemplate.from_template(template)
    else:
        message = ChatMessagePromptTemplate.from_template(template, role=role)
    return message


def _convert_to_message(
    message: Union[
        BaseMessagePromptTemplate,
        BaseMessage,
        Tuple[str, str],
        Tuple[Type, str],
        str,
    ]
) -> Union[BaseMessage, BaseMessagePromptTemplate]:
    """Instantiate a message from a variety of message formats.

    The message format can be one of the following:

    - BaseMessagePromptTemplate
    - BaseMessage
    - 2-tuple of (role string, template); e.g., ("human", "{user_input}")
    - 2-tuple of (message class, template)
    - string: short-hand for ("human", template); e.g., "{user_input}"

    Args:
        message: a representation of a message in one of the supported formats

    Returns:
        an instance of a message or a message template
    """
    if isinstance(message, BaseMessagePromptTemplate):
        _message = message
    elif isinstance(message, BaseMessage):
        _message = message
    elif isinstance(message, str):
        _message = _create_template_from_role_string("human", message)
    elif isinstance(message, tuple):
        if len(message) != 2:
            raise ValueError(f"Expected 2-tuple of (role, template), got {message}")
        role, template = message
        if isinstance(role, str):
            _message = _create_template_from_role_string(role, template)
        else:
            _message = role(prompt=PromptTemplate.from_template(template))
    else:
        raise NotImplementedError(f"Unsupported message type: {type(message)}")

    return _message
