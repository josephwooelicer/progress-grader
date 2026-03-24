# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project Overview

> **TODO:** Fill in project description after initial setup.

## Spec-Driven Design Workflow

This project follows a **spec-driven design** approach. All features must be fully specified before implementation begins.

### Workflow Steps

1. **Spec** — Write a detailed spec in `specs/` before touching any code.
2. **Design** — Document architecture decisions in `design/`.
3. **Implement** — Write code only after spec and design are approved.
4. **Test** — Verify against the spec, not just the implementation.

### Directory Structure

```
specs/          # Feature specs (.md files)
design/         # Architecture and design documents
src/            # Source code (do not create without a spec)
tests/          # Tests (mirror spec acceptance criteria)
```

## Development Guidelines

- Do not write implementation code without a corresponding spec in `specs/`.
- Each spec file should follow the template in `specs/TEMPLATE.md`.
- Design documents should reference the spec they are derived from.
- Keep specs updated when requirements change — the spec is the source of truth.

## Commands

> **TODO:** Add build, test, and run commands once the stack is decided.
