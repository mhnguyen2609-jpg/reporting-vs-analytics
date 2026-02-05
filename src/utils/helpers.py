
import re

def natural_sort_key(s):
    """
    Key for natural sorting (e.g., 1, 2, 10 instead of 1, 10, 2).
    Usage: sorted(list, key=natural_sort_key)
    """
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', str(s))]
