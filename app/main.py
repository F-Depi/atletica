from nicegui import ui
from pages import rankings
from components.header import create_header

@ui.page('/')
def home():
    create_header()
    
    with ui.column().classes('w-full max-w-4xl mx-auto p-4 gap-6'):
        ui.markdown('''
        # Benvenuto su AtleticaDB
        
        Questo sito raccoglie e organizza le graduatorie nazionali italiane dal 2005 ad oggi,
        offrendo uno strumento di consultazione semplice, veloce e il più completo possibile.
        ''').classes('text-gray-300')
        
        with ui.card().classes('w-full'):
            with ui.row().classes('items-center justify-between w-full'):
                with ui.column():
                    ui.label('Rankings').classes('text-2xl text-blue-400 font-bold')
                    ui.link('Vai alla pagina →', '/rankings').classes('text-blue-300')
                
                with ui.column().classes('text-gray-400'):
                    ui.label("• Un'unica pagina per tutti i risultati dal 2005 ad oggi")
                    ui.label('• Graduatorie nazionali anche per ragazzi ed esordienti')
                    ui.label('• Filtri per regione, provincia e società')
        
        with ui.card().classes('w-full'):
            ui.label('Statistiche').classes('text-2xl text-blue-400 font-bold')
            ui.label('Prossimamente...').classes('text-gray-500')

# Importa le altre pagine DOPO aver definito la home
# (questo registra le route)

ui.run(
    title='AtleticaDB',
    dark=True,
    port=8080,
    favicon='🏃'
)
