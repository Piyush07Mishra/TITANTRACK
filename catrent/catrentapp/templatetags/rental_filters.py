from django import template
import builtins

register = template.Library()

@register.filter
def abs_filter(value):
    try:
        return abs(int(value))
    except:
        return value

@register.filter
def progress_percent(days_remaining, rental):
    try:
        if rental.expected_end_date and rental.start_date:
            total = (rental.expected_end_date - rental.start_date).days
            elapsed = total - days_remaining
            if total <= 0:
                return 100
            pct = int((elapsed / total) * 100)
            return max(0, min(100, pct))
    except:
        pass
    return 50
