from django.utils import timezone
from datetime import timedelta

def get_date_range(days=7):
    """Get date range for queries"""
    today = timezone.now().date()
    start_date = today - timedelta(days=days)
    return start_date, today

def format_date_range(start_date, end_date):
    """Format date range for display"""