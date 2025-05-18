from flask import Blueprint

from app.app import DISCIPLINES


# Create blueprint
error_reporting_bp = Blueprint('error_reporting', __name__)


def should_show_wind(discipline, ambiente):
    # Don't show wind for indoor events
    if ambiente == 'I':
        return False
    
    # Get discipline info
    discipline_info = DISCIPLINES[discipline]
    
    # Don't show wind if discipline doesn't use it
    if discipline_info.get('vento') != 'sì':
        return False
    
    return True


def format_time(seconds, discipline_info, cronometraggio):
    """Format time based on discipline type, duration and cronometraggio"""
    tot_digits = 5
    decimal_digits = 2

    ## Prove multiple sono un punteggio
    if discipline_info['tipo'] == 'Prove Multiple':
        return f"{seconds:.0f}"

    ## To manual timings 0.24s is added in prestazione for the rankings, but we
    ## now want to display the original time with 1 decimal digit
    if cronometraggio == 'm':
        seconds -= 0.24
        decimal_digits = 1
        tot_digits = 4

    ## Anche i salti e i lanci non vogliono avere lo 0 se sono < 10
    if seconds < 10:
            return f"{seconds:0{tot_digits - 1}.{decimal_digits}f}"

    ## I tempi li mettiamo in formato MM:SS.sss altrimenti gliuis si lamenta
    if discipline_info['classifica'] == 'tempo' and seconds >= 60:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:0{tot_digits}.{decimal_digits}f}"
    return f"{seconds:0{tot_digits}.{decimal_digits}f}"
