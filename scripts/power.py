"""
power.py
Sample size calculator and test power analysis for CRO experiments.

Used by the agent to validate whether a proposed experiment has enough traffic
to reach statistical significance in a reasonable timeframe.

Usage:
  # How many sessions per variant for a 10% relative lift?
  python scripts/power.py --baseline-cvr 2.0 --mde 10

  # Can we run a 3-way MVT with 5000 weekly sessions?
  python scripts/power.py --baseline-cvr 2.0 --mde 10 --variants 3 --weekly-sessions 5000

  # How long will an A/B test take?
  python scripts/power.py --baseline-cvr 1.8 --mde 15 --weekly-sessions 3200
"""

import argparse
import math


def required_sample_per_variant(
    baseline_cvr: float,
    mde_relative: float,
    power: float = 0.80,
    alpha: float = 0.05,
) -> int:
    """
    Calculates the required sample size per variant for a two-proportion z-test.

    Args:
        baseline_cvr: Current conversion rate as a percentage (e.g. 2.0 for 2%)
        mde_relative: Minimum detectable effect as relative percentage (e.g. 10 for 10% relative lift)
        power: Statistical power (default 0.80)
        alpha: Significance level, two-tailed (default 0.05)

    Returns:
        Required sessions per variant (integer, rounded up)
    """
    p1 = baseline_cvr / 100
    p2 = p1 * (1 + mde_relative / 100)

    # z-scores for alpha/2 and power
    z_alpha = _z_score(1 - alpha / 2)
    z_power = _z_score(power)

    # Pooled standard deviation
    p_bar = (p1 + p2) / 2

    numerator = (z_alpha * math.sqrt(2 * p_bar * (1 - p_bar)) +
                 z_power * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    denominator = (p2 - p1) ** 2

    if denominator == 0:
        return float('inf')

    return math.ceil(numerator / denominator)


def test_duration_weeks(
    sample_per_variant: int,
    num_variants: int,
    weekly_sessions: int,
) -> float:
    """
    Calculates how many weeks a test needs to run.

    Args:
        sample_per_variant: Required sessions per variant
        num_variants: Number of variants including control (2 for A/B, 3 for A/B/C)
        weekly_sessions: Total weekly sessions to the page being tested

    Returns:
        Duration in weeks (float)
    """
    total_required = sample_per_variant * num_variants
    if weekly_sessions == 0:
        return float('inf')
    return total_required / weekly_sessions


def assess_test_viability(
    baseline_cvr: float,
    mde_relative: float,
    num_variants: int,
    weekly_sessions: int,
    max_weeks: int = 6,
    power: float = 0.80,
    alpha: float = 0.05,
) -> dict:
    """
    Full viability assessment for a proposed experiment.

    Returns a dict with sample size, duration, and recommendations.
    """
    sample = required_sample_per_variant(baseline_cvr, mde_relative, power, alpha)
    total_required = sample * num_variants
    weeks = test_duration_weeks(sample, num_variants, weekly_sessions)

    viable = weeks <= max_weeks
    test_type = "A/B" if num_variants == 2 else f"{num_variants}-way MVT"

    # Recommendations based on playbook.md thresholds
    recommendations = []

    if weekly_sessions < 2000:
        recommendations.append("Traffic below 2,000/week: A/B only, no MVT.")
        if num_variants > 2:
            recommendations.append(f"UNDERPOWERED: {test_type} not viable at this traffic level. Switch to A/B.")
    elif weekly_sessions < 8000:
        if num_variants > 3:
            recommendations.append(f"Traffic 2k-8k/week: max 2-way MVT. {test_type} may be underpowered.")
        else:
            recommendations.append("Traffic supports A/B or 2-way MVT in independent zones.")
    else:
        recommendations.append(f"Traffic > 8k/week: {test_type} with up to 4 variants is viable.")

    if not viable:
        # Suggest alternatives
        if num_variants > 2:
            alt_sample = required_sample_per_variant(baseline_cvr, mde_relative, power, alpha)
            alt_weeks = test_duration_weeks(alt_sample, 2, weekly_sessions)
            recommendations.append(
                f"At current traffic, this {test_type} would take {weeks:.1f} weeks. "
                f"Switching to A/B would take {alt_weeks:.1f} weeks."
            )
        # Suggest larger MDE
        for bigger_mde in [15, 20, 25, 30]:
            alt_sample = required_sample_per_variant(baseline_cvr, bigger_mde, power, alpha)
            alt_weeks = test_duration_weeks(alt_sample, num_variants, weekly_sessions)
            if alt_weeks <= max_weeks:
                recommendations.append(
                    f"To fit within {max_weeks} weeks, target a {bigger_mde}% relative MDE "
                    f"(requires {alt_sample:,} sessions/variant, {alt_weeks:.1f} weeks)."
                )
                break

    return {
        "baseline_cvr": baseline_cvr,
        "mde_relative": mde_relative,
        "test_type": test_type,
        "num_variants": num_variants,
        "sample_per_variant": sample,
        "total_sessions_required": total_required,
        "weekly_sessions": weekly_sessions,
        "estimated_weeks": round(weeks, 1),
        "viable": viable,
        "max_weeks": max_weeks,
        "power": power,
        "alpha": alpha,
        "recommendations": recommendations,
    }


def _z_score(p: float) -> float:
    """Inverse normal CDF approximation (Abramowitz and Stegun)."""
    if p <= 0 or p >= 1:
        raise ValueError(f"Probability must be between 0 and 1, got {p}")

    if p < 0.5:
        return -_z_score(1 - p)

    t = math.sqrt(-2 * math.log(1 - p))
    c0 = 2.515517
    c1 = 0.802853
    c2 = 0.010328
    d1 = 1.432788
    d2 = 0.189269
    d3 = 0.001308

    return t - (c0 + c1 * t + c2 * t**2) / (1 + d1 * t + d2 * t**2 + d3 * t**3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CRO Experiment Power Calculator")
    parser.add_argument("--baseline-cvr", type=float, required=True,
                        help="Current conversion rate as percentage (e.g. 2.0)")
    parser.add_argument("--mde", type=float, default=10,
                        help="Minimum detectable effect as relative %% (default: 10)")
    parser.add_argument("--variants", type=int, default=2,
                        help="Number of variants including control (default: 2 for A/B)")
    parser.add_argument("--weekly-sessions", type=int, default=0,
                        help="Weekly sessions to the page being tested")
    parser.add_argument("--max-weeks", type=int, default=6,
                        help="Maximum acceptable test duration in weeks (default: 6)")
    parser.add_argument("--power", type=float, default=0.80,
                        help="Statistical power (default: 0.80)")
    parser.add_argument("--alpha", type=float, default=0.05,
                        help="Significance level (default: 0.05)")
    args = parser.parse_args()

    result = assess_test_viability(
        baseline_cvr=args.baseline_cvr,
        mde_relative=args.mde,
        num_variants=args.variants,
        weekly_sessions=args.weekly_sessions,
        max_weeks=args.max_weeks,
        power=args.power,
        alpha=args.alpha,
    )

    print(f"\n{'='*50}")
    print(f"  POWER ANALYSIS")
    print(f"{'='*50}")
    print(f"  Baseline CVR:     {result['baseline_cvr']}%")
    print(f"  Target MDE:       {result['mde_relative']}% relative lift")
    print(f"  Test type:        {result['test_type']}")
    print(f"  Power:            {result['power']:.0%}")
    print(f"  Significance:     {result['alpha']}")
    print(f"")
    print(f"  Sessions/variant: {result['sample_per_variant']:,}")
    print(f"  Total required:   {result['total_sessions_required']:,}")

    if args.weekly_sessions > 0:
        print(f"  Weekly sessions:  {result['weekly_sessions']:,}")
        print(f"  Estimated weeks:  {result['estimated_weeks']}")
        print(f"  Viable (<{result['max_weeks']}wk):   {'YES' if result['viable'] else 'NO'}")

    if result["recommendations"]:
        print(f"\n  Recommendations:")
        for r in result["recommendations"]:
            print(f"  - {r}")

    print()
