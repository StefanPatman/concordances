# Concordance Scoring — Plain-Language Guide

## What we are scoring

We have several **candidate partitions**. A partition is one way of splitting the
individuals into groups (subsets = putative species). We want to know which partition is
best supported by the evidence.

The evidence comes as **concordances** — independent lines of evidence (a morphological
character, a geographic gap, etc.). For scoring, each line gives a simple **yes/no**
answer for every *pair of subsets*: "yes, these two groups look like separate species by
this line of evidence" or "no, they don't". Each line of evidence can also carry a
**weight** if some sources are considered more trustworthy than others.

So the raw material for every partition is: for each pair of subsets, how many (weighted)
lines of evidence say "yes, these are distinct".

---

## The central problem: more subsets are easier to support

If you split individuals into more groups, you create more boundaries to check — and
smaller groups are easier to tell apart, so more of those boundaries get a "yes" just by
chance. A naive score therefore keeps going up the more you split, which pushes you toward
nonsense partitions where every individual is its own species.

The interesting question for every score below is:

> **The fairness test:** if *all* the evidence is supportive, should a partition with many
> subsets score the same as one with few subsets?

We think the answer should usually be **yes** — with perfect evidence there is no reason to
prefer fewer or more groups. Scores should only start preferring fewer groups when the
evidence is *incomplete or noisy* (where extra subsets mainly add lucky "yes" answers).

Running example used throughout: **10 lines of evidence, each weight 1**, and every line
supports every boundary (the "perfect" case). We compare a partition with **3 subsets**
(3 pairs of subsets) against one with **6 subsets** (15 pairs).

The scores fall into three families depending on how they treat subset count.

---

## Family 1 — Scores that reward splitting (do NOT correct)

### CSU — total support
Simply adds up all the "yes" votes (times their weights) across every pair of subsets.

- Perfect case: 3 subsets → 30, 6 subsets → 150.
- **Fails the fairness test badly.** More subsets means more pairs to collect "yes" votes
  from, so the number just keeps climbing. On its own this score always favours splitting.
  It is really a raw total, useful only as an ingredient for the scores below.

---

## Family 2 — Scores that are fair (flat when evidence is perfect)

These all boil the evidence down to a **rate** — "what fraction of the checks came back
yes" — instead of a raw count. A rate does not care how many pairs there are, so with
perfect evidence it lands on the same value no matter how many subsets you have.

### CSW — average support per pair
Takes CSU and divides by the number of subset pairs. This turns the growing total into an
average per boundary.

- Perfect case: 3 subsets → 10, 6 subsets → 10. **Passes the fairness test.**
- Interpretation: the average weighted support each boundary receives. Higher is better.

### CSWC — average support per pair, adjusted for coverage
Like CSW, but each boundary's contribution is scaled down if only a few lines of evidence
actually tested it. A boundary checked by 2 of 10 lines counts for less than one checked
by all 10. This guards against a boundary looking strong just because it was barely
examined.

- Perfect case (every line tests every boundary): same as CSW, so 10 for both. **Passes.**
- Higher is better.

### BayesMean — average confidence per boundary
For each boundary it computes a **confidence** between 0 and 1: "given the yes/no votes,
how sure are we this is a real boundary?" A boundary with no evidence sits at 0.5
(a coin flip); one with lots of "yes" votes climbs toward 1. It then takes the (geometric)
average of these confidences across all boundaries. The geometric average is strict: one
badly-supported boundary drags the whole partition down.

- Perfect case: every boundary reaches the same confidence (about 0.95 with 10 lines), so
  the average is ~0.95 for both 3 and 6 subsets. **Passes.**
- The exact ceiling depends on how many lines of evidence you have, not on subset count.
- Higher is better; 0.5 means "no information".

### BayesMin — confidence of the weakest boundary
Same per-boundary confidence as BayesMean, but instead of averaging it reports the
**single worst** boundary. A partition only scores well if *every* boundary is supported.

- Perfect case: all boundaries share the same confidence, so it matches BayesMean (~0.95)
  for both partitions. **Passes.**
- The strictest of the "fair" scores — very sensitive to a single unsupported boundary.
  Higher is better.

### BayesLogFactor — how much better than random
For each boundary it asks: are these votes more consistent with a *real* boundary
(expected to draw "yes" about 80% of the time) or a *random* one (50%)? It tallies the
evidence for "real vs random" across boundaries and squeezes the result into a 0-to-1
value. Importantly, a "no" vote counts against a boundary more than a "yes" vote counts
for it, so scattered disagreement is punished.

- Perfect case: every boundary gives the same "clearly real" reading regardless of subset
  count, so 3 and 6 subsets score alike. **Passes.**
- Higher is better; 0.5 means "no better than random".

---

## Family 3 — Scores that deliberately penalise splitting

These start from how well the evidence fits, then **subtract a penalty that grows with the
number of subsets**. They intentionally do *not* pass the fairness test: given two
perfectly-supported partitions they prefer the one with fewer groups, on the principle
that the simpler explanation should win unless the extra groups earn their keep. This is
the classic "parsimony" / Occam's-razor idea.

All three share the same first step: measure the overall concordance rate (how often the
evidence said "yes"), which — like the Family 2 scores — is itself fair to subset count.
The difference is entirely in the penalty they add on top.

### BIC — fit minus a strong complexity penalty
Rewards good evidence fit, then subtracts a penalty proportional to the number of subsets
(scaled by the size of the dataset). The penalty is fairly heavy, so BIC leans strongly
toward fewer groups.

- Perfect case: the fit is identical for 3 and 6 subsets, but the 6-subset partition pays a
  bigger penalty, so it scores **worse**. **Deliberately fails the fairness test.**
- **Lower is better** (unlike the scores above).

### AIC — fit minus a lighter complexity penalty
Same idea as BIC but with a gentler, fixed penalty per subset that ignores dataset size.
It still prefers fewer groups, just less aggressively than BIC — so it will tolerate more
subsets before saying "too much".

- Perfect case: 6 subsets still scores worse than 3, but by a smaller margin than under BIC.
- **Lower is better.**

### BayesPP — probability that this is the right partition
Combines the evidence fit with a preference for fewer subsets, then **normalises across all
candidate partitions** so the values form probabilities that add up to 1 (e.g. "partition A
42%, partition B 31%..."). This is the most directly interpretable output.

- Perfect case: even with identical fit, the partition with fewer subsets is assigned a
  higher probability. **Deliberately fails the fairness test.**
- Higher is better. Because it is normalised, adding or removing candidate partitions
  changes everyone's value.
- The strength of the "prefer fewer subsets" preference is a tunable setting.

---

## Two constraint checks (not scores)

These just check the partition against prior knowledge you supply, and report yes/no.

- **CC (conspecific check):** are individuals you said belong together actually placed in
  the same subset? Reports `True` if all such groups are kept together.
- **HC (heterospecific check):** are individuals you said belong apart actually placed in
  different subsets? Reports `True` if none of them were lumped together.

---

## Summary

| Score | Better = | Treats subset count how? | Passes fairness test? |
|-------|----------|--------------------------|------------------------|
| CSU | higher | rewards more subsets (raw total) | No — favours splitting |
| CSW | higher | neutral (average per boundary) | **Yes** |
| CSWC | higher | neutral, plus coverage adjustment | **Yes** |
| BayesMean | higher | neutral (average confidence) | **Yes** |
| BayesMin | higher | neutral (weakest boundary) | **Yes** |
| BayesLogFactor | higher | neutral (evidence vs random) | **Yes** |
| BIC | **lower** | penalises more subsets (strong) | No — by design |
| AIC | **lower** | penalises more subsets (light) | No — by design |
| BayesPP | higher | penalises more subsets (tunable) | No — by design |
| CC / HC | True | not applicable (a check) | — |

**How to read this:** the Family 2 scores tell you *how good the evidence is* without
taking a stance on how many species there should be — with perfect evidence they can't
distinguish a 3-way from a 6-way split. The Family 3 scores take that stance for you,
building in a preference for fewer species. If your goal is to have the "right" number of
subsets rise to the top automatically, a Family 3 score is what does that work; if you
want to judge evidence quality and decide on subset count yourself, a Family 2 score keeps
those two questions separate.
