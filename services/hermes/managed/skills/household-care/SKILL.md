---
name: household-care
description: "Record and query 1-year-old diet and stool data via Mealie and Baby Buddy MCP tools."
version: 1.0.0
author: home-services
license: MIT
metadata:
  hermes:
    tags: [care, baby, diet, stool, mealie, babybuddy, household]
    category: household
---

# Household Care

This is the canonical entry point for recording and querying our 1-year-old's diet
and stool consistency. Mealie is the source of truth for meals and recipes; Baby
Buddy is the source of truth for growth and medical/stool entries.

## Recording a meal

1. Identify the food from the user's message. If it maps to an existing Mealie
   recipe or ingredient, reference it by name; do not create duplicates.
2. Record the entry through the Mealie MCP tools (recipe or meal log) with the
   date, portion, and who ate it.
3. Confirm what you recorded back to the user in one short sentence.

## Recording a stool entry

1. Use the Baby Buddy MCP tools to create the stool entry with the date and the
   reported consistency (Bristol scale when the user gives a number, otherwise the
   best-matching description).
2. Do not invent values the user did not provide; if the consistency is unclear,
   ask once.
3. Confirm the entry back to the user in one short sentence.

## Querying

- "What did [child] eat today?" -> query Mealie meal logs for today.
- "How has [child]'s stool been this week?" -> query Baby Buddy stool entries for
  the last 7 days and summarize the trend (count, consistency range).
- Keep answers short and factual; do not give medical advice. If a pattern looks
  concerning, say so plainly and suggest the pediatrician, without diagnosing.

## Boundaries

- Record only what the user says. Do not fabricate meals, portions, dates, or
  consistency.
- If a tool call is denied or fails, say what failed; do not silently retry or
  guess.
- Confirm the exact target before a permanent delete.
- Configuration and server changes are outside this skill's scope.
