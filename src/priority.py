def assign_priority_tier(top_third_risk, incidence_at_or_above_avg):
    """
    Assign Priority / Watch / Stable classification.

    Priority:
        Top-third structural risk AND
        2025 incidence >= five-year average.

    Watch:
        Exactly one of the two conditions is true.

    Stable:
        Neither condition is true.
    """

    if top_third_risk and incidence_at_or_above_avg:
        return "Priority"

    if top_third_risk or incidence_at_or_above_avg:
        return "Watch"

    return "Stable"