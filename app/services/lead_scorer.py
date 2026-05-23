def score_lead(budget_max: int | None, listing_price_max: int | None, timeline_days: int | None) -> tuple[str, str]:
    """
    Simple budget-alignment + urgency scoring.
    Returns (score_tag, reason_string).
    """
    if not budget_max or not listing_price_max:
        return 'WARM', 'Budget or listing price unknown — manual review recommended'
    
    budget_ratio = budget_max / listing_price_max
    
    if budget_ratio >= 0.85 and timeline_days and timeline_days <= 60:
        return 'HOT', f'Budget {budget_ratio:.0%} of listing price, wants to move in {timeline_days}d'
    
    elif budget_ratio >= 0.7 or (timeline_days and timeline_days <= 120):
        return 'WARM', f'Budget at {budget_ratio:.0%}, timeline {timeline_days}d'
    
    else:
        return 'COLD', f'Budget {budget_ratio:.0%} of listing — likely window shopper'
