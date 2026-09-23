# Risk model

Three scores per state, 0 (easy) to 5 (hard):

- `water`: water stress and cooling constraint.
- `zoning`: local permitting and political friction.
- `incentives`: how little the state offers (5 means nothing on the table).

The map shades states by the mean of whatever scores are present. Site
ranking multiplies a site's fit by `(1 - risk / 10)`, so a maximum-risk state
loses half its score. One number, visible in the code, easy to change.

What it is not: these are inputs you supply, not a measurement. The demo
values are random and the legend says so. Real scores should come from
Aqueduct (water), county permitting records (zoning) and published incentive
programs (incentives).
