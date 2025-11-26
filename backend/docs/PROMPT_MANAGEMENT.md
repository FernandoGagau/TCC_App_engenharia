# Prompt Management Guide

## Overview

All system prompts are centralized in `backend/config/prompts.yaml` for better control, versioning, and maintenance. The `PromptManager` class provides a clean interface to access these prompts.

## Architecture

### Files Involved

1. **`backend/config/prompts.yaml`** - Centralized prompt definitions
2. **`backend/src/infrastructure/config/prompt_manager.py`** - Prompt loading and management
3. **Agent files** - Should use PromptManager instead of hardcoded prompts

### Prompt Structure in YAML

```yaml
agents:
  supervisor:
    role: "Supervisor de Análise de Construção"
    system_prompt: |
      Main system prompt for the agent...

    intent_analysis_system: "System message for intent analysis"
    intent_analysis_prompt: |
      Detailed prompt with {placeholders}...

    final_response_system: "System message for final response"
    final_response_prompt: |
      Prompt with variables like {summary}, {findings}...

  visual:
    system_prompt: |
      Visual agent system prompt...
    comprehensive_analysis_prompt: |
      Prompt for image analysis...
    phase_detection_system: |
      Phase detection system message...
    # ... more prompts
```

## Using PromptManager in Agents

### Basic Usage

```python
from infrastructure.config.prompt_manager import get_prompt_manager

class MyAgent:
    def __init__(self):
        self.prompt_manager = get_prompt_manager()

    async def process(self):
        # Get system prompt
        system_prompt = self.prompt_manager.get_system_prompt('visual')

        # Get specific prompt with variables
        analysis_prompt = self.prompt_manager.get_prompt(
            'visual',
            'comprehensive_analysis_prompt'
        )

        # Get prompt with variable substitution
        progress_prompt = self.prompt_manager.get_prompt(
            'visual',
            'progress_calculation_system',
            location_context='área externa'
        )
```

### Convenience Functions

```python
from infrastructure.config.prompt_manager import (
    get_supervisor_prompts,
    get_visual_prompts,
    get_document_prompts,
    get_progress_prompts,
    get_report_prompts
)

# Get all prompts for an agent at once
supervisor_prompts = get_supervisor_prompts()
system_prompt = supervisor_prompts['system_prompt']
intent_prompt = supervisor_prompts['intent_analysis_prompt']
```

## Migration Examples

### Before (Hardcoded Prompts)

```python
# supervisor.py - BEFORE
prompt = f"""
Analise esta solicitação do usuário e determine o tipo de tarefa:

Entrada do usuário: {user_input}
Tem anexos: {len(attachments) if attachments else 0}
...
"""

messages = [
    {"role": "system", "content": "Você é um especialista..."},
    {"role": "user", "content": prompt}
]
```

### After (Using PromptManager)

```python
# supervisor.py - AFTER
from infrastructure.config.prompt_manager import get_prompt_manager

pm = get_prompt_manager()

# Get system message
system_message = pm.get_prompt('supervisor', 'intent_analysis_system')

# Get prompt with variables
prompt = pm.get_prompt(
    'supervisor',
    'intent_analysis_prompt',
    user_input=user_input,
    attachment_count=len(attachments) if attachments else 0,
    attachment_types=str([a.get('type') for a in attachments] if attachments else []),
    context_history=context_text
)

messages = [
    {"role": "system", "content": system_message},
    {"role": "user", "content": prompt}
]
```

## Prompts Available by Agent

### Supervisor Agent

**Core Prompts:**
- `system_prompt` - Main supervisor system prompt
- `final_response_system` - System message for final response generation
- `final_response_prompt` - Prompt for generating final response (vars: context_history, summary, key_findings, recommendations, next_steps, errors)

**Onboarding Flow (NEW):**
- `check_project_exists_system` - System message for checking if user has projects
- `check_project_exists_prompt` - Prompt to verify projects in database (vars: has_projects, project_count, project_list, user_input, context_history)
- `onboarding_welcome_system` - System message for welcoming new users
- `onboarding_welcome_prompt` - Initial onboarding questions (vars: user_input)
- `onboarding_collect_info_system` - System message for progressive info collection
- `onboarding_collect_info_prompt` - Collect project info step by step (vars: collected_info, user_input, context_history, missing_info)
- `project_confirmation_system` - System message for confirming project data
- `project_confirmation_prompt` - Confirm collected information (vars: project_info)

**Project Management:**
- `intent_analysis_system` - System message for intent classification
- `intent_analysis_prompt` - User prompt for intent analysis (vars: user_input, attachment_count, attachment_types, available_projects, context_history)
- `project_selection_system` - System message for project selection
- `project_selection_prompt` - Help user select project (vars: project_list, user_input, current_project, context_history)
- `missing_project_error_system` - System message for missing project errors
- `missing_project_error_prompt` - Guide user when project is missing (vars: requested_action, available_projects)

### Visual Agent

- `system_prompt` - Main visual agent system prompt
- `comprehensive_analysis_prompt` - Prompt for comprehensive image analysis
- `phase_detection_system` - System message for phase detection
- `safety_detection_system` - System message for safety issue detection
- `progress_calculation_system` - Prompt for progress calculation (vars: location_context)

### Document Agent

- `system_prompt` - Main document agent system prompt
- `specification_extraction_system` - System message for spec extraction
- `specification_extraction_prompt` - Prompt for extracting specifications (vars: text)
- `schedule_parsing_system` - System message for schedule parsing
- `schedule_parsing_prompt` - Prompt for parsing schedules (vars: text)
- `project_info_extraction_system` - System message for project info extraction
- `project_info_extraction_prompt` - Prompt for extracting project info (vars: text)

### Progress Agent

- `system_prompt` - Main progress agent system prompt
- `delay_analysis_system` - System message for delay analysis
- `delay_analysis_prompt` - Prompt for analyzing delays (vars: delays, bottlenecks)
- `prediction_insights_system` - System message for prediction insights
- `prediction_insights_prompt` - Prompt for prediction insights (vars: progress_percentage, predicted_completion, original_deadline)

### Report Agent

- `system_prompt` - Main report agent system prompt
- `narrative_generation_system` - System message for narrative generation
- `narrative_generation_prompt` - Prompt for generating narratives (vars: report_type, report_data)
- `executive_summary_system` - System message for executive summaries
- `executive_summary_prompt` - Prompt for executive summary (vars: executive_data)
- `recommendations_system` - System message for recommendations
- `recommendations_prompt` - Prompt for generating recommendations (vars: analysis_data)

## Benefits of Centralized Prompts

1. **Version Control**: Track prompt changes in git
2. **Easy Updates**: Modify prompts without touching code
3. **Consistency**: Ensure all agents use standardized prompts
4. **A/B Testing**: Easy to test prompt variations
5. **Translation**: Easier to maintain multilingual prompts
6. **Documentation**: Prompts are self-documenting in YAML
7. **Hot Reload**: Can reload prompts without restarting (in development)

## Development Tips

### Reloading Prompts

During development, you can reload prompts without restarting:

```python
pm = get_prompt_manager()
pm.reload_prompts()  # Reloads from YAML file
```

### Adding New Prompts

1. Add the prompt to `backend/config/prompts.yaml` under the appropriate agent
2. Use descriptive keys like `task_name_prompt` or `task_name_system`
3. Use `{variable}` syntax for placeholders
4. Update this documentation with the new prompt

### Prompt Best Practices

1. **Use Variables**: Make prompts flexible with `{variable}` placeholders
2. **System vs User**: Separate system instructions from user prompts
3. **JSON Responses**: Include JSON schema examples in prompts
4. **Language**: Keep Portuguese for BR users, English for technical specs
5. **Structure**: Use clear sections and bullet points
6. **Length**: Keep prompts focused and concise

## Testing Prompts

```python
import pytest
from infrastructure.config.prompt_manager import get_prompt_manager

def test_prompt_loading():
    pm = get_prompt_manager()

    # Test system prompt exists
    system_prompt = pm.get_system_prompt('supervisor')
    assert system_prompt, "Supervisor system prompt should exist"

    # Test variable substitution
    prompt = pm.get_prompt(
        'supervisor',
        'intent_analysis_prompt',
        user_input="test",
        attachment_count=0,
        attachment_types="[]",
        context_history=""
    )
    assert "test" in prompt, "Variable substitution should work"
```

## Migration Checklist

- [ ] All supervisor.py prompts migrated to YAML
- [ ] All visual_agent.py prompts migrated to YAML
- [ ] All document_agent.py prompts migrated to YAML
- [ ] All progress_agent.py prompts migrated to YAML
- [ ] All report_agent.py prompts migrated to YAML
- [ ] Update agent files to use PromptManager
- [ ] Add tests for prompt loading
- [ ] Document all prompt variables
- [ ] Review and optimize prompt texts
- [ ] Add version control for prompts

## Future Enhancements

1. **Prompt Versioning**: Track prompt versions with semantic versioning
2. **Multilingual Support**: Add language-specific prompt sections
3. **Prompt Analytics**: Track which prompts perform best
4. **Dynamic Prompts**: Load prompts based on user preferences or context
5. **Prompt Templates**: Support nested templates and includes
6. **Validation**: Schema validation for prompt variables