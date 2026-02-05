def remove_consecutive_duplicates(steps):
    """Remove consecutive duplicate steps based on action and locator."""
    if not steps:
        return steps
    
    deduplicated = [steps[0]]
    
    for i in range(1, len(steps)):
        current = steps[i]
        previous = deduplicated[-1]
        
        # Check if consecutive steps are duplicates
        is_duplicate = (
            current['action'] == previous['action'] and
            current['locators']['stable'] == previous['locators']['stable']
        )
        
        if not is_duplicate:
            deduplicated.append(current)
    
    # Renumber steps
    for idx, step in enumerate(deduplicated, 1):
        step['step'] = idx
    
    return deduplicated
