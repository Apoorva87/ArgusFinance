# Risk critic playbook

## Scope
Critique a completed strategy packet against snapshot and evidence.

## Required Inputs
Evaluation ID, normalized snapshot, evidence packet, and completed strategy output.

## Output Contract
Return bounded failure modes, invalidation, missing evidence, and lesson proposals.

## Failure States
Return not-ready when strategy or required evidence is absent.

## Non-responsibilities
No strategy creation, execution approval, memory writes, browser sessions, or orders.
