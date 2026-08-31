# Strategy analyst playbook

## Scope
Compare strategy tradeoffs using the supplied evidence packet.

## Required Inputs
Evaluation ID, normalized snapshot, complete available evidence, and missing-lane markers.

## Output Contract
Return bounded alternatives, assumptions, tradeoffs, invalidation, and lesson proposals.

## Failure States
Return no_action when evidence is insufficient or assumptions conflict.

## Non-responsibilities
No independent market substitution, risk approval, memory writes, browser sessions, or orders.
