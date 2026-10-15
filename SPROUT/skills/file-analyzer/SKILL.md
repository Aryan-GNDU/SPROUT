---
name: file-analyzer
description: Analyze files and provide structured summaries
---

# File Analyzer Skill

When asked to analyze a local file, follow these steps:

## Step 1: Read the Content

For a local file, use the `read_file` tool with its workspace-relative path.
If the user provides a URL, explain that URL fetching is not supported yet.

## Step 2: Analyze the Structure

Identify:
- The type of document (README, documentation, code, article, etc.)
- Main sections and their purposes
- Key topics covered

## Step 3: Provide Structured Output

Always format your analysis as:

**Document Type**: [type of document]

**Purpose**: [one sentence describing the main purpose]

**Sections**:
- [Section 1]: [brief description]
- [Section 2]: [brief description]
- ...

**Key Points**:
- [Important point 1]
- [Important point 2]
- [Important point 3]

**Summary**: [2-3 sentence summary of the entire document]

## Guidelines

- Be concise but comprehensive
- Focus on the most important information
- If the document is code-related, mention technologies and dependencies
- If it's a README, highlight installation and usage instructions