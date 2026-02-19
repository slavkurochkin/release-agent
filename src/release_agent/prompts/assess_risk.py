"""Prompt templates for the release risk assessment agent.

This module contains the system and user prompt templates that instruct
the LLM how to analyze release data and produce risk assessments.

Prompt engineering principles applied here:
1. Clear persona and role definition
2. Explicit output format with JSON schema
3. Step-by-step reasoning instructions
4. Few-shot examples for calibration
5. Guardrails against common failure modes

The prompts are designed to work with OpenAI's JSON mode, so the LLM
is instructed to respond ONLY with valid JSON matching the output schema.
"""

from __future__ import annotations

import json

from release_agent.schemas import ReleaseInput, ReleaseOutput

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a Release Risk Assessment Agent. Your job is to analyze
release metadata and produce a structured risk assessment.

## Your Role
You are an experienced SRE/release engineer who has seen thousands of deployments.
You are cautious but pragmatic — you don't block releases without good reason,
but you catch real risks that humans might miss.

## What You Analyze
- File changes: what code is being modified and where
- CI results: did automated checks pass or fail
- Commit messages: do they indicate risky changes (migrations, auth, infra)
- Recent incidents: is the team already dealing with production issues
- Deployment target: production vs staging changes risk profile

## Risk Calibration Guidelines
- **LOW (0.0-0.3)**: Documentation, tests, minor UI tweaks, config changes
  in non-critical paths. Routine changes with small blast radius.
- **MEDIUM (0.3-0.5)**: Business logic changes, new features behind flags,
  dependency updates with good test coverage. Small changes deployed during
  active incidents (when the change is unrelated to the incident).
- **HIGH (0.5-0.7)**: Database migrations, authentication changes, API
  contract modifications, changes touching payment/billing code. Clean CI
  with comprehensive test coverage is a strong mitigating factor — a major
  auth refactor (e.g. session→JWT) with all tests passing, security scan
  clean, and no active incidents is HIGH and GO, not CRITICAL.
- **CRITICAL (0.7-1.0)**: Infrastructure changes without rollback plan,
  multiple high-risk areas changed simultaneously, CI failures on critical
  checks.

## Risk Modifiers
Active incidents raise risk but do NOT automatically make a deploy CRITICAL.
Consider the change scope: a 2-file logging change during a DB incident is
still LOW-MEDIUM risk for that change. Conversely, deploying a large auth
refactor during an active incident compounds risk significantly.

## Decision Rules
- **GO**: Risk is manageable, changes are well-tested, no blocking issues.
  May include conditions (e.g., "monitor error rates for 30 minutes").
- **NO_GO**: Unacceptable risk identified. Always explain what must change.

## Output Format
You MUST respond with valid JSON matching this exact schema:
{schema}

## Important
- Always provide specific, actionable reasoning — not vague concerns
- Reference specific files and changes in your explanation
- If CI checks failed, that's a strong signal — explain why you'd still GO if you do
- Consider the COMBINATION of risk factors, not just individual ones
- A database migration + auth change + deploy during incident = CRITICAL
"""

# ---------------------------------------------------------------------------
# User Prompt Template
# ---------------------------------------------------------------------------

USER_PROMPT_TEMPLATE = """Assess the risk of the following release:

## Release Information
- **Repository**: {repo}
- **PR**: #{pr_number}
- **Title**: {title}
- **Author**: {author}
- **Target**: {deployment_target}

## Description
{description}

## Files Changed ({num_files} files, +{total_additions}/-{total_deletions})
{files_section}

## CI Results
{ci_section}

## Commit Messages
{commits_section}

## Recent Incidents
{incidents_section}

Analyze this release and provide your risk assessment as JSON."""


# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------


def build_system_prompt() -> str:
    """Build the system prompt with the output schema injected.

    Returns:
        The complete system prompt string with JSON schema included.
    """
    # TODO: Build the system prompt by injecting the ReleaseOutput JSON schema.
    #
    # Steps:
    # 1. Generate the JSON schema from ReleaseOutput:
    #    schema = ReleaseOutput.model_json_schema()
    #
    # 2. Format it as a pretty-printed JSON string:
    #    import json
    #    schema_str = json.dumps(schema, indent=2)
    #
    # 3. Inject it into SYSTEM_PROMPT:
    #    return SYSTEM_PROMPT.format(schema=schema_str)
    #
    # Hint: The {schema} placeholder in SYSTEM_PROMPT is where it goes.
    schema = ReleaseOutput.model_json_schema()
    schema_str = json.dumps(schema, indent=2)
    return SYSTEM_PROMPT.format(schema=schema_str)


def build_user_prompt(release: ReleaseInput) -> str:
    """Build the user prompt from a ReleaseInput instance.

    This formats all the release data into a human-readable prompt that
    gives the LLM the context it needs to assess risk.

    Args:
        release: The release data to format into a prompt

    Returns:
        The formatted user prompt string
    """
    # TODO: Build the user prompt by formatting the release data.
    #
    # Steps:
    # 1. Build the files section — for each file in release.files_changed:
    #    - Format as: "- `{path}` (+{additions}/-{deletions})"
    #    - If the file has a patch, include it in a code block
    #    - If no files, use "No file changes provided."
    #
    # 2. Build the CI section — for each result in release.ci_results:
    #    - Format as: "- {name}: {'PASSED' if passed else 'FAILED'}"
    #    - If there are details, include them
    #    - If no CI results, use "No CI results provided."
    #
    # 3. Build the commits section — for each message in release.commit_messages:
    #    - Format as: "- {message}"
    #    - If no commits, use "No commit messages provided."
    #
    # 4. Build the incidents section — for each incident in release.recent_incidents:
    #    - Format as: "- {incident}"
    #    - If no incidents, use "No recent incidents."
    #
    # 5. Calculate totals:
    #    - num_files = len(release.files_changed)
    #    - total_additions = sum of all additions
    #    - total_deletions = sum of all deletions
    #
    # 6. Return USER_PROMPT_TEMPLATE.format(...) with all the values
    #
    # Hint: Use "\n".join() to combine list items into sections.
    # Files section
    if release.files_changed:
        files_lines = []
        for f in release.files_changed:
            line = f"- `{f.path}` (+{f.additions}/-{f.deletions})"
            files_lines.append(line)
            if f.patch:
                files_lines.append(f"  ```\n  {f.patch}\n  ```")
        files_section = "\n".join(files_lines)
    else:
        files_section = "No file changes provided."

    # CI section
    if release.ci_results:
        ci_lines = []
        for ci in release.ci_results:
            status = "PASSED" if ci.passed else "FAILED"
            line = f"- {ci.name}: {status}"
            if ci.details:
                line += f" -- {ci.details}"
            ci_lines.append(line)
        ci_section = "\n".join(ci_lines)
    else:
        ci_section = "No CI results provided."

    # Commits section
    if release.commit_messages:
        commits_section = "\n".join(f"- {msg}" for msg in release.commit_messages)
    else:
        commits_section = "No commit messages provided."

    # Incidents section
    if release.recent_incidents:
        incidents_section = "\n".join(f"- {inc}" for inc in release.recent_incidents)
    else:
        incidents_section = "No recent incidents."

    # Totals
    num_files = len(release.files_changed)
    total_additions = sum(f.additions for f in release.files_changed)
    total_deletions = sum(f.deletions for f in release.files_changed)

    return USER_PROMPT_TEMPLATE.format(
        repo=release.repo,
        pr_number=release.pr_number,
        title=release.title,
        author=release.author,
        deployment_target=release.deployment_target,
        description=release.description or "No description provided.",
        num_files=num_files,
        total_additions=total_additions,
        total_deletions=total_deletions,
        files_section=files_section,
        ci_section=ci_section,
        commits_section=commits_section,
        incidents_section=incidents_section,
    )
