---
name: task-extraction
description: Pull concrete tasks with owners and due dates out of free-form text. Use when the user pastes notes or asks what they need to do.
---
# Task extraction

Use this skill to turn loose text into a list of tasks someone could act on.

## Steps
1. Read the text and find statements that commit someone to an action.
2. Ignore ideas, opinions and background unless someone agreed to act on them.
3. For each task, record the action, the owner and the due date.
4. Merge duplicates, keeping the most specific wording.

## Output
A list with one task per line in this form:
`- [owner] action (due: date)`

Use `unassigned` when no owner is stated and `no date` when no date is stated.

## Rules
- Start each task with a verb.
- Never guess an owner or a date.
- If there are no tasks, reply `No tasks found.`
