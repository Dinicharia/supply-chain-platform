# Analytics Findings

Findings from Phase 6 exploratory analysis of the synthetic inventory simulation. Queries referenced live in `sql/analytics/`.

---

## Finding 1: Overall stockout rate is 10.68%

Across all 12.64M simulated facility-commodity-days (2021-2025), 10.68% of days show zero closing stock. This is the platform's headline "Executive Overview" metric.

## Finding 2: Larger facilities have modestly lower stockout rates

| Facility Tier | Stockout Rate |
|---|---|
| Health Center | 11.09% |
| Dispensary | 10.93% |
| Sub-County Hospital | 10.39% |
| County/Referral Hospital | 8.35% |

**Explanation:** larger facilities carry proportionally larger absolute stock buffers, and Poisson-distributed demand has *relatively* less variance at higher volumes (a real inventory-theory phenomenon sometimes called the "square root law" of safety stock). Larger operations are inherently more stable relative to their own scale, even before accounting for any policy differences.

## Finding 3: Regional variation is modest and not a direct simulation driver

Regional stockout rates range narrowly from 10.07% (Northeastern) to 11.50% (Nairobi). This is expected: region is not itself a mechanistic input to the simulation (facility tier and commodity are) - regional variation here is purely emergent from *which* facility tiers/commodities happen to be concentrated in each region. If the platform were extended to model real geographic risk factors (e.g., remoteness affecting supplier lead times), region would need to become a direct driver, not just an indirect one.

## Finding 4 (most important): Commodity consumption volume dominates criticality in driving stockout risk

Essential commodities (14 of 16) show stockout rates of 8-16%, while the two Routine commodities (LLIN, Paracetamol) show dramatically lower rates (3.11% and 0.49%) - the **opposite** of what a naive reading of "Essential gets tighter reorder policy" would predict.

**Root cause:** the simulation's `REORDER_POLICY` (10-day reorder trigger for Essential vs. 20-day for Routine) is a real, working mechanism, but its protective effect is currently outweighed by two other factors that happen to correlate with several Essential/low-volume commodities in this dataset:
- **Low baseline consumption volume** (`BASE_CONSUMPTION`): low-volume commodities have proportionally noisier day-to-day demand relative to their own stock levels ("lumpy demand"), making them statistically harder to keep reliably stocked regardless of reorder policy.
- **Seasonality**: malaria commodities carry a 1.3-1.6x seasonal consumption multiplier during Kenya's rainy seasons, which the current reorder-point policy does not anticipate (it reacts to low stock, but doesn't forecast the upcoming seasonal surge).

**Business implication (synthetic-data-derived, not a real-world claim):** in this model, a resupply-prioritization system based on criticality alone would be insufficient - it would systematically under-protect low-volume, seasonal, or high-demand-variability commodities relative to high-volume routine ones. A more effective real-world system would weight commodity demand volatility and seasonality alongside criticality, and/or use forecast-aware (rather than purely reactive) reorder policies for seasonal commodities.

This finding is a property of our synthetic simulation's current parameters, not a real-world empirical claim about Kenya's health supply chain - documented here for transparency, consistent with the project's synthetic-data disclosure principles (see README).

---

*Last updated: Phase 6 (Analytics)*