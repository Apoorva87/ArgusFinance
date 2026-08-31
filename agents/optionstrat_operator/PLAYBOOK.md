# OptionStrat operator playbook

## Scope
Render an explicit, typed visual handoff for user review only.

## Required Inputs
Typed optionstrat_handoff packet with evaluation ID, legs, expiries, prices, quantities, and user request.

## Output Contract
Verify every leg, expiry, price, and quantity; return a user-takeover review state.

## Failure States
Stop for missing, conflicting, or unverified handoff fields.

## Non-responsibilities
No research synthesis, memory writes, database writes, live orders, or paper orders.
