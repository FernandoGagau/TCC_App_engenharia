# Onboarding Flow Implementation

## Summary

This document describes the onboarding flow implementation that guides users who have no projects in the database through a conversational process to collect project information.

## Changes Made

### 1. Supervisor Agent (`src/agents/supervisor.py`)

**Added Project Check Method:**
- `_check_user_has_projects()`: Checks database for user projects
- Returns project count and list
- Falls back gracefully if repository unavailable

**Enhanced Intent Analysis:**
- Before analyzing intent, checks if user has projects
- If no projects AND first message → triggers onboarding
- Uses `check_project_exists_prompt` to determine if onboarding needed
- Returns `CHAT_INTERACTION` task type with `needs_onboarding` flag

**Enhanced Final Response Generation:**
- Detects onboarding flag in task details
- Uses `onboarding_welcome_prompt` to generate friendly welcome message
- Asks about what user wants to analyze/monitor
- Falls back to default message if LLM fails

### 2. Test Updates (`tests/test_prompt_manager.py`)

**Fixed Variable Test:**
- Added missing `available_projects` parameter to `test_get_prompt_with_variables`
- Now all tests pass

## How It Works

### First Message Flow (No Projects):

1. **User sends first message** → Supervisor receives message
2. **Supervisor checks database** → `_check_user_has_projects()`
3. **No projects found** → Triggers onboarding logic
4. **LLM confirms onboarding needed** → Uses `check_project_exists_prompt`
5. **Returns CHAT_INTERACTION task** → With `needs_onboarding: true` flag
6. **Generates welcome response** → Uses `onboarding_welcome_prompt`
7. **User receives friendly message** → Asking what they want to analyze

### Example Response:

```
"Olá! Vejo que você ainda não tem nenhum projeto cadastrado.
Vamos começar! Me conta um pouco sobre o que você gostaria de
analisar ou acompanhar?"
```

### Subsequent Messages:

- Once user provides information, supervisor can collect details progressively
- Uses `onboarding_collect_info_prompt` for follow-up questions
- Eventually creates project in database

## Integration Points

### Database Check:
```python
project_repository.get_all()  # Gets all projects
# TODO: Filter by user_id when auth is implemented
```

### Onboarding Trigger:
```python
if not project_check["has_projects"] and len(conversation_history) == 0:
    # Trigger onboarding
    return TaskType.CHAT_INTERACTION, {
        "needs_onboarding": True,
        "reason": "Nenhum projeto cadastrado",
        "response_type": "onboarding_welcome"
    }
```

### Response Generation:
```python
task_details = state['context'].get('task_details', {})
if task_details.get('needs_onboarding', False):
    # Generate onboarding welcome message
    onboarding_prompt = self.prompt_manager.get_prompt(
        'supervisor',
        'onboarding_welcome_prompt',
        user_input=user_input
    )
```

## Prompts Used

1. **check_project_exists_prompt**: Analyzes if onboarding is needed
   - Variables: `has_projects`, `project_count`, `project_list`

2. **onboarding_welcome_prompt**: Generates friendly welcome message
   - Variables: `user_input`

3. **onboarding_collect_info_prompt**: Collects project information progressively
   - Variables: `collected_info`, `user_input`, `context_history`, `missing_info`

## Testing

Run tests to verify implementation:

```bash
python3 -m pytest tests/test_prompt_manager.py -v
python3 -m pytest tests/test_prompt_variables.py -v
```

## Next Steps

1. **Implement project creation**: After collecting information, create project in database
2. **Add session state tracking**: Track onboarding progress across messages
3. **User authentication**: Filter projects by actual user_id
4. **Frontend integration**: Handle onboarding UI flow
5. **Progressive information collection**: Implement 2-3 question rounds

## Notes

- Onboarding only triggers on FIRST message when no projects exist
- Falls back gracefully if any step fails
- Uses centralized prompt system for consistency
- Logging added for debugging onboarding flow