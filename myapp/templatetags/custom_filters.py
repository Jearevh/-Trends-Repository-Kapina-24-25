from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
@stringfilter
def truncate_chars(value, max_length):
    if len(value) > max_length:
        return value[:max_length] + '...'
    return value

@register.filter
def default_if_none(value, default=""):
    return value if value is not None else default

@register.filter
def format_time(value):
    if not value:
        return ""
    try:
        # Assuming value is in HH:MM format
        return value.strftime("%I:%M %p") if hasattr(value, 'strftime') else value
    except:
        return value

@register.filter
def format_business_hours(business):
    """
    Format business hours for the current day.
    Returns formatted string like '8:00 AM - 11:00 PM' or 'Closed' if the business is closed.
    """
    if not business:
        return "Hours not specified"
    
    try:
        from datetime import datetime
        current_day = datetime.now().strftime('%A').lower()
        
        # Try to get hours for current day
        hours = business.operating_hours.filter(day=current_day).first()
        
        if not hours:
            return "Hours not specified"
            
        if hours.is_closed:
            return "Closed"
            
        opening = datetime.strptime(hours.opening_time, '%H:%M').strftime('%I:%M %p')
        closing = datetime.strptime(hours.closing_time, '%H:%M').strftime('%I:%M %p')
        return f"{opening} - {closing}"
    except Exception:
        return "Hours not specified"

@register.filter
def sub(value, arg):
    """Subtracts the arg from the value."""
    try:
        return int(value) - len(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def get_range(value):
    """Returns a range of numbers from 0 to value."""
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return range(0)

@register.filter
def multiply(value, arg):
    """Multiplies the value by the argument."""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0 