"""
Base agent class that all RepoZen agents inherit from.

Uses Azure OpenAI as the LLM backend.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
)


def get_llm(
    temperature: float = 0.2,
    deployment: Optional[str] = None,
) -> AzureChatOpenAI:
    """Create an Azure OpenAI LLM instance.

    Args:
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
        deployment: Override the default deployment name

    Returns:
        AzureChatOpenAI instance ready to use with LangChain
    """
    return AzureChatOpenAI(
        azure_deployment=deployment or AZURE_OPENAI_DEPLOYMENT,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        temperature=temperature,
    )


class BaseAgent(ABC):
    """Abstract base for all RepoZen agents.

    Provides:
      - A shared LLM instance (Azure OpenAI)
      - A helper to invoke prompt → LLM → parser chains
      - A standard `run()` interface every agent must implement
    """

    def __init__(self, temperature: float = 0.2):
        self.llm = get_llm(temperature=temperature)

    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """Execute the agent's primary task. Must be implemented by subclasses."""
        ...

    def _invoke_chain(
        self,
        prompt: ChatPromptTemplate,
        variables: Dict[str, Any],
        parser=None,
    ) -> Any:
        """Helper to run a prompt chain with optional output parsing.

        Args:
            prompt: The ChatPromptTemplate to use
            variables: Dict of template variables to fill in
            parser: Optional LangChain output parser (e.g. JsonOutputParser)

        Returns:
            Parsed output if parser is provided, otherwise raw LLM response
        """
        if parser:
            chain = prompt | self.llm | parser
        else:
            chain = prompt | self.llm

        return chain.invoke(variables)