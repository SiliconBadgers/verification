# Verification and confidence in the design: team charter

## Purpose

Develop justified confidence in the accelerator by asking what it should do, what could invalidate that expectation and what evidence is sufficient for the claims being made. The team helps the project understand correctness, uncertainty and risk across component and system boundaries.

Verification is a form of investigation as well as implementation. Useful work can clarify an ambiguous requirement, construct a counterexample, compare verification methods, reason about a protocol, develop a test environment or explain where existing evidence is incomplete. The team’s remit is broader than running other teams’ tests.

## Responsibilities

### Correctness interpretation

Work with specification and implementation teams to make requirements observable and assessable. Identify ambiguity, contradictory assumptions and behavior that has not yet been defined.

### Independent assessment

Choose verification approaches appropriate to the claim: review, modeling, simulation, assertions, formal reasoning or other methods. Preserve independence of reasoning even when artifacts are shared.

### Coverage and limitations

Explain what evidence covers, how it was obtained and which behaviors or operating conditions remain uncertain. Distinguish a passing example from a justified broader claim.

### Verification knowledge

Maintain reusable reasoning, environments, findings and educational material. Help members understand failure modes and how verification can shape a design before or during implementation.

## Boundaries and shared decisions

Verification stewards independent assessment; each component team remains responsible for the quality and local validation of its work. Architecture and affected teams resolve intended semantics together. ml-models supplies reference behavior with stated assumptions. Accelerator organizes combined-system evidence and demonstrations. Verification communicates findings and confidence rather than unilaterally selecting system priorities or assigning implementation work.

## Member autonomy

Members may choose a correctness question, examine a specification, investigate a verification technique, develop a model, explore formal properties, build test infrastructure or analyze a failure. The method should fit the question; no framework or coverage metric is prescribed here. Changes to intended behavior are agreed with the responsible teams, while findings can challenge any existing assumption.

## Collaboration

| Partners | Shared concerns |
|---|---|
| architecture and ml-models | Clarify intended behavior and numerical assumptions, and investigate where references or specifications may themselves be incomplete. |
| RTL and software teams | Exchange observable behavior, design intent and findings. Support actionable interpretation of mismatches without replacing component-owned validation. |
| fpga, physical-design and accelerator | Help distinguish functional, platform and implementation claims, and explain which evidence supports each. |

## Possible directions

Possible directions include a protocol counterexample, a reset-behavior study, a survey of formal techniques, a useful assertion, an independent scoreboard, a failure investigation or a guide to interpreting coverage. Members choose meaningful questions rather than a fixed queue of test-writing assignments.

## What progress means

Progress means the project makes better-supported claims, discovers important misunderstandings and understands the remaining uncertainty. Finding an unsupported assumption, narrowing a confidence claim or documenting a useful verification method can be valuable even when no bug is found.

Leads help members interpret this purpose, find collaborators, access resources
and share what they learn. Members choose their questions and contributions.
Research, design reasoning, experiments, implementation, documentation and
teaching can all advance the charter; success is not measured by the number of
code changes or completed tickets.

The team can revise this charter as its understanding evolves. Changes to a
shared boundary or commitment are discussed with the teams affected by them.
The [objectives](OBJECTIVES.md) describe durable outcomes, and the
[repository structure](README.md#repository-structure) provides places to develop
work without specifying a mandatory project or sequence.
