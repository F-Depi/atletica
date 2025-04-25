from app.routes import statistics_bp
from flask import render_template

@statistics_bp.route('/')
def statistics():
    # For initial development with 3 placeholder statistics
    stats = [
        {
            'id': 1,
            'title': 'Evoluzione record nazionali',
            'description': 'Analisi dell\'evoluzione dei record nazionali dal 2005 ad oggi nelle principali discipline.',
            'visualization_type': 'chart',
            'chart_type': 'line',
            'chart_data': {
                'labels': ['2005', '2010', '2015', '2020', '2024'],
                'datasets': [{
                    'label': '100m Uomini',
                    'data': [10.1, 10.05, 10.01, 9.99, 9.95],
                    'borderColor': 'rgba(75, 192, 192, 1)',
                }]
            },
            'chart_options': {},
            'has_details': True
        },
        {
            'id': 2,
            'title': 'Distribuzione risultati elite',
            'description': 'Visualizzazione della distribuzione dei migliori risultati italiani nelle varie discipline.',
            'visualization_type': 'chart',
            'chart_type': 'bar',
            'chart_data': {
                'labels': ['<11.0', '11.0-11.5', '11.5-12.0', '12.0-12.5', '>12.5'],
                'datasets': [{
                    'label': '100m Donne',
                    'data': [5, 15, 25, 35, 20],
                    'backgroundColor': 'rgba(153, 102, 255, 0.6)',
                }]
            },
            'chart_options': {},
            'has_details': True
        },
        {
            'id': 3,
            'title': 'Confronto stagioni',
            'description': 'Confronto delle performance degli atleti italiani tra diverse stagioni agonistiche.',
            'visualization_type': 'chart',
            'chart_type': 'radar',
            'chart_data': {
                'labels': ['100m', '200m', '400m', '800m', '1500m', '5000m'],
                'datasets': [
                    {
                        'label': '2023',
                        'data': [90, 85, 88, 81, 76, 70],
                        'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                        'borderColor': 'rgba(255, 99, 132, 1)',
                    },
                    {
                        'label': '2024',
                        'data': [92, 88, 84, 83, 82, 74],
                        'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                        'borderColor': 'rgba(54, 162, 235, 1)',
                    }
                ]
            },
            'chart_options': {},
            'has_details': True
        }
    ]
    
    return render_template('statistics.html', stats=stats)

@statistics_bp.route('/statistics/snt:stat_id>')
def statistic_detail(stat_id):
    # Fetch the specific statistic detail
    # This is where you'd run your specific PostgreSQL queries
    
    # Example placeholder
    stat = {
        'id': stat_id,
        'title': f'Statistica Dettagliata {stat_id}',
        'description': 'Visualizzazione approfondita dei dati.',
        'content': 'Contenuto dettagliato della statistica...'
    }
    
    return render_template('statistic_detail.html', stat=stat)
