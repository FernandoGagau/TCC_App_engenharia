"""
Prompt Manager - Centralized Prompt Management
Loads and manages all prompts from prompts.yaml configuration
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Centralized manager for all system prompts
    Loads prompts from prompts.yaml and provides easy access
    """

    _instance = None
    _prompts: Dict[str, Any] = {}

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super(PromptManager, cls).__new__(cls)
            cls._instance._load_prompts()
        return cls._instance

    def _load_prompts(self) -> None:
        """Load prompts from YAML file"""
        try:
            # Find prompts.yaml in config directory
            config_path = Path(__file__).parent.parent.parent.parent / "config" / "prompts.yaml"

            if not config_path.exists():
                logger.error(f"Prompts file not found at {config_path}")
                self._prompts = {}
                return

            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                self._prompts = data.get('agents', {})
                logger.info(f"Loaded prompts for {len(self._prompts)} agents")

        except Exception as e:
            logger.error(f"Error loading prompts: {str(e)}")
            self._prompts = {}

    def get_agent_prompts(self, agent_name: str) -> Dict[str, Any]:
        """
        Get all prompts for a specific agent

        Args:
            agent_name: Name of the agent (supervisor, visual, document, progress, report)

        Returns:
            Dictionary with all prompts for the agent
        """
        return self._prompts.get(agent_name, {})

    def get_prompt(self, agent_name: str, prompt_key: str, **kwargs) -> str:
        """
        Get a specific prompt for an agent with variable substitution

        Args:
            agent_name: Name of the agent
            prompt_key: Key of the prompt to retrieve
            **kwargs: Variables to substitute in the prompt template

        Returns:
            Formatted prompt string
        """
        agent_prompts = self.get_agent_prompts(agent_name)
        prompt_template = agent_prompts.get(prompt_key, "")

        if not prompt_template:
            logger.warning(f"Prompt '{prompt_key}' not found for agent '{agent_name}'")
            return ""

        # Substitute variables in the template
        try:
            return prompt_template.format(**kwargs)
        except KeyError as e:
            missing_var = str(e).strip("'\"")
            logger.error(
                f"Missing variable '{missing_var}' in prompt '{prompt_key}' for agent '{agent_name}'. "
                f"Available variables: {list(kwargs.keys())}. "
                f"Returning template without substitution."
            )
            return prompt_template
        except Exception as e:
            logger.error(f"Error formatting prompt '{prompt_key}': {str(e)}")
            return prompt_template

    def get_system_prompt(self, agent_name: str) -> str:
        """
        Get the system prompt for an agent

        Args:
            agent_name: Name of the agent

        Returns:
            System prompt string
        """
        return self.get_prompt(agent_name, 'system_prompt')

    def reload_prompts(self) -> None:
        """Reload prompts from YAML file (useful for development)"""
        self._load_prompts()


# Global singleton instance
_prompt_manager = None


def get_prompt_manager() -> PromptManager:
    """
    Get the global PromptManager instance

    Returns:
        PromptManager singleton instance
    """
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


# Convenience functions for common operations

def get_supervisor_prompts() -> Dict[str, str]:
    """Get all supervisor agent prompts"""
    pm = get_prompt_manager()
    return pm.get_agent_prompts('supervisor')


def get_visual_prompts() -> Dict[str, str]:
    """Get all visual agent prompts"""
    pm = get_prompt_manager()
    return pm.get_agent_prompts('visual')


def get_document_prompts() -> Dict[str, str]:
    """Get all document agent prompts"""
    pm = get_prompt_manager()
    return pm.get_agent_prompts('document')


def get_progress_prompts() -> Dict[str, str]:
    """Get all progress agent prompts"""
    pm = get_prompt_manager()
    return pm.get_agent_prompts('progress')


def get_report_prompts() -> Dict[str, str]:
    """Get all report agent prompts"""
    pm = get_prompt_manager()
    return pm.get_agent_prompts('report')