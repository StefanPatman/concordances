from pathlib import Path
from time import perf_counter
import math
from collections import defaultdict

from ..common.types import Results
from .types import OpenResults


def initialize():
    import itaxotools

    itaxotools.progress_handler("Initializing...")
    import core  # noqa
    import itaxotools.taxi2.sequences  # noqa
    import itaxotools.spart_parser  # noqa


def open_spart(path: Path):
    from itaxotools.spart_parser import Spart

    if not path.is_file():
        return OpenResults({}, {})

    spart = Spart.fromXML(path)

    concordance_data: dict[str, dict[str, object]] = {}

    for spartition in spart.getSpartitions():
        concordances = spart.getSpartitionConcordances(spartition)
        for concordance in concordances:
            data = spart.getConcordanceData(spartition, concordance)
            if concordance not in concordance_data:
                concordance_data[concordance] = data
            else:
                assert concordance_data[concordance] == data

    individuals_list = spart.getIndividuals()

    return OpenResults(concordance_data, individuals_list)


def execute(
    concordance_path: Path,
    output_path: Path,
    concordance_weights: dict[str, float],
    evidence_types_weights: dict[str, float],
    evidence_types_behaviours: dict[str, bool],
    conspecific_constraints: list[list[str]],
    heterospecific_constraints: list[list[str]],
) -> Results:
    from itaxotools.spart_parser import Spart

    print(f"{concordance_weights=}")
    print(f"{evidence_types_weights=}")
    print(f"{evidence_types_behaviours=}")
    print(f"{conspecific_constraints=}")
    print(f"{heterospecific_constraints=}")

    ts = perf_counter()

    spart = Spart.fromXML(concordance_path)

    N = len(spart.getIndividuals())

    # Assumed concordance rate for a real boundary (H1) vs random (H0),
    # used for the log Bayes factor score.
    THETA_1 = 0.8
    THETA_0 = 0.5
    LOG_BF_SUPPORT = math.log(THETA_1 / THETA_0)
    LOG_BF_NO_SUPPORT = math.log((1 - THETA_1) / (1 - THETA_0))

    # Prior penalty per species for BayesPP (PDF 1).
    # Higher λ = stronger preference for fewer species.
    LAMBDA = 0.1

    # Strength of the size-based neutral chance model used by BayesMeanCC.
    # A pair of subsets with n_a, n_b individuals is assigned a chance
    # concordance rate 1 / (1 + n_a·n_b / (β·N)): smaller subsets look
    # "distinct" by chance more easily, so the mean chance rate rises with the
    # number of subsets. Smaller β = higher assumed chance rate = stronger
    # discount. Tune to taste, or replace θ0 with an empirical estimate from
    # reshuffled partitions (see SCORES.md).
    CHANCE_BETA = 0.05

    # Collected per-spartition for BayesPP normalization after the main loop.
    bayes_pp_data: list[tuple[str, float]] = []

    for spartition in spart.getSpartitions():
        subsets = spart.getSpartitionSubsets(spartition)
        if len(subsets) < 2:
            continue

        score: int = 0
        score_c: float = 0.0
        support_table: dict[tuple[int, int], float] = defaultdict(lambda: 0.0)
        support_table_cap: dict[tuple[int, int], int] = defaultdict(lambda: 0)
        # total weight per pair (concordant + non-concordant), for Bayesian scoring
        weighted_total_table: dict[tuple[int, int], float] = defaultdict(lambda: 0.0)
        # accumulated log Bayes factor per pair
        log_bf_table: dict[tuple[int, int], float] = defaultdict(lambda: 0.0)
        # weight-weighted sum of the neutral chance rate, over every test
        # (line × pair), for BayesMeanCC
        chance_weighted: float = 0.0
        combinations = math.comb(len(subsets), 2)
        evidence_types_totals: dict[str, int] = defaultdict(lambda: 0)
        concordance_evidence_types: dict[str, str] = {}
        final_concordance_weights: dict[str, float] = {}

        for concordance in spart.getSpartitionConcordances(spartition):
            if concordance not in concordance_weights:
                continue
            data = spart.getConcordanceData(spartition, concordance)
            evidence_type = data["evidenceType"]
            concordance_evidence_types[concordance] = evidence_type
            evidence_types_totals[evidence_type] += concordance_weights[concordance]

        for concordance, weight in concordance_weights.items():
            evidence_type = concordance_evidence_types[concordance]
            weight *= evidence_types_weights[evidence_type]
            if not evidence_types_behaviours[evidence_type]:
                weight /= evidence_types_totals[evidence_type]
            final_concordance_weights[concordance] = weight

        for concordance in spart.getSpartitionConcordances(spartition):
            if concordance not in concordance_weights:
                continue
            for limit in spart.getConcordantLimits(spartition, concordance):
                sub_a = limit["subsetnumberA"]
                sub_b = limit["subsetnumberB"]
                sub_a, sub_b = sorted([sub_a, sub_b])
                concordant = limit["concordanceSupport"]
                if not isinstance(concordant, bool):
                    raise TypeError(
                        f"concordanceSupport for '{concordance}' is {type(concordant).__name__}, "
                        "not bool — only Boolean concordances should be scored"
                    )
                weight = final_concordance_weights[concordance]
                support = weight if concordant else 0.0
                score += support
                support_table[(sub_a, sub_b)] += support
                support_table_cap[(sub_a, sub_b)] += 1
                weighted_total_table[(sub_a, sub_b)] += weight
                log_bf_table[(sub_a, sub_b)] += weight * (
                    LOG_BF_SUPPORT if concordant else LOG_BF_NO_SUPPORT
                )
                n_a = limit["NIndividualsSubsetA"]
                n_b = limit["NIndividualsSubsetB"]
                chance_weighted += weight * (
                    1.0 / (1.0 + (n_a * n_b) / (CHANCE_BETA * N))
                )
        for limit in support_table:
            score_c += support_table[limit] * (
                support_table_cap[limit] / len(concordance_weights)
            )

        spart.addSpartitionData(
            spartition,
            CSU=score,
            CSW=score / combinations,
            CSWm=score / combinations / len(subsets),
            CSWC=score_c / combinations,
        )

        if support_table:
            # Per-pair Bayesian posterior using a Jeffreys Beta(0.5, 0.5) prior.
            # Rate = weighted support fraction in [0,1]; count (n) = number of
            # concordances that actually tested this pair (unweighted). Separating
            # rate from count ensures large total weights don't push posteriors to
            # floor — n governs uncertainty, rate governs the estimate.
            # Neutral value (n=0): 0.5 / 1 = 0.5.
            pair_posteriors = {}
            for pair in support_table:
                n = support_table_cap[pair]
                rate = support_table[pair] / weighted_total_table[pair]
                pair_posteriors[pair] = (rate * n + 0.5) / (n + 1.0)

            # BayesMean: geometric mean of all pair posteriors.
            # High when most boundaries are consistently well-supported.
            log_sum = sum(math.log(p) for p in pair_posteriors.values())
            bayes_mean = math.exp(log_sum / len(pair_posteriors))

            # BayesMin: minimum pair posterior.
            # High only when every boundary has support — weakest-link criterion.
            bayes_min = min(pair_posteriors.values())

            # BayesLogFactor: per-pair log Bayes factor scaled by concordance count
            # (H1: real boundary, expected rate=0.8; H0: random, rate=0.5), then
            # mean across pairs and converted to probability via sigmoid.
            pair_log_bfs = {}
            for pair in support_table:
                n = support_table_cap[pair]
                rate = support_table[pair] / weighted_total_table[pair]
                pair_log_bfs[pair] = n * (
                    rate * LOG_BF_SUPPORT + (1.0 - rate) * LOG_BF_NO_SUPPORT
                )
            mean_log_bf = sum(pair_log_bfs.values()) / len(pair_log_bfs)
            bayes_log_factor = 1.0 / (1.0 + math.exp(-mean_log_bf))

            spart.addSpartitionData(
                spartition,
                BayesMean=bayes_mean,
                BayesMin=bayes_min,
                BayesLogFactor=bayes_log_factor,
            )

            # Partition-level scores (PDF 1 & PDF 2).
            # p_hat is the true weighted concordance rate in [0,1]: weighted
            # concordant tests over weighted total tests. It is independent of K,
            # so large partitions are not penalised merely for having more pairs.
            # E (effective evidence lines) = total concordance weight, also
            # independent of C(K,2), so likelihood magnitudes stay comparable across
            # partitions. S = p_hat * E. Laplace smoothing keeps p strictly inside
            # (0,1) so log(p) and log(1-p) are always defined.
            weighted_total = sum(weighted_total_table.values())
            p_hat = score / weighted_total if weighted_total else 0.0
            E = sum(final_concordance_weights.values())
            S = p_hat * E
            K = len(subsets)
            p = (S + 0.5) / (E + 1.0)
            log_L = S * math.log(p) + (E - S) * math.log(1.0 - p)

            # BayesMeanC (Fix 1): composition/coverage-invariant "corrected
            # BayesMean". A single Jeffreys Beta(0.5, 0.5) posterior on the
            # pooled concordance rate p_hat, with prior strength E (evidence
            # lines, independent of K) instead of the per-pair coverage that
            # makes plain BayesMean drift with subset count. Any two partitions
            # with the same weighted concordance proportion get an identical
            # score, whatever their number or composition of subsets. Neutral
            # value (p_hat=0.5): 0.5. Higher is better.
            bayes_mean_c = (S + 0.5) / (E + 1.0)

            # BayesMeanCC (Fix 2): BayesMeanC additionally corrected for the
            # chance that more (hence smaller) subsets score "yes" more readily.
            # theta_0 is the weighted mean neutral chance rate; it rises with K.
            # kappa is the excess concordance over chance (Cohen's-kappa form),
            # then Jeffreys-smoothed exactly like BayesMeanC. Perfect support
            # (p_hat=1) always gives kappa=1, but partial support is discounted
            # more heavily the larger K is. Higher is better; 0.5/(E+1) means
            # "no better than chance".
            theta_0 = chance_weighted / weighted_total if weighted_total else 0.0
            kappa = (
                max(0.0, (p_hat - theta_0) / (1.0 - theta_0)) if theta_0 < 1.0 else 0.0
            )
            bayes_mean_cc = (kappa * E + 0.5) / (E + 1.0)

            spart.addSpartitionData(
                spartition,
                BayesMeanC=bayes_mean_c,
                BayesMeanCC=bayes_mean_cc,
            )

            # BIC / AIC: lower is better.
            log_N = math.log(N) if N > 1 else 1.0
            spart.addSpartitionData(
                spartition,
                BIC=-2.0 * log_L + K * log_N,
                AIC=-2.0 * log_L + 2.0 * K,
            )

            # Collect unnormalized log-posterior for BayesPP.
            # Prior exp(-λK) penalizes many species (over-splitting).
            bayes_pp_data.append((spartition, log_L + (-LAMBDA * K)))

        def check_conspecific() -> bool:
            for subset in spart.getSpartitionSubsets(spartition):
                subset_individuals = spart.getSubsetIndividuals(spartition, subset)
                for group_individuals in conspecific_constraints:
                    for individual in group_individuals:
                        if individual not in subset_individuals:
                            continue
                        for other in group_individuals:
                            if other == individual:
                                continue
                            if other not in subset_individuals:
                                return False
            return True

        def check_heterospecific() -> bool:
            for subset in spart.getSpartitionSubsets(spartition):
                subset_individuals = spart.getSubsetIndividuals(spartition, subset)
                for group_individuals in heterospecific_constraints:
                    for individual in group_individuals:
                        if individual not in subset_individuals:
                            continue
                        for other in group_individuals:
                            if other == individual:
                                continue
                            if other in subset_individuals:
                                return False
            return True

        spart.addSpartitionData(spartition, CC="True" if check_conspecific() else "No")
        spart.addSpartitionData(
            spartition, HC="True" if check_heterospecific() else "No"
        )

    # BayesPP: normalize across all spartitions → true posterior probability.
    # Uses log-sum-exp trick for numerical stability.
    if bayes_pp_data:
        log_vals = [lp for _, lp in bayes_pp_data]
        max_lv = max(log_vals)
        denom = sum(math.exp(lp - max_lv) for lp in log_vals)
        for spartition_label, log_posterior in bayes_pp_data:
            spart.addSpartitionData(
                spartition_label,
                BayesPP=math.exp(log_posterior - max_lv) / denom,
            )

    spart.toXML(output_path)

    tf = perf_counter()

    return Results(output_path, tf - ts)
