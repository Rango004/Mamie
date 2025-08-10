from django import template

register = template.Library()

@register.filter
def replace_underscore(value):
    """Replace underscores with spaces and title case"""
    return str(value).replace('_', ' ').title()