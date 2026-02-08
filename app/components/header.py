from nicegui import ui
from database import search_athletes, search_societies


def create_header():
    """Header riutilizzabile con search"""
    
    with ui.header().classes('bg-gray-900 p-0'):
        with ui.row().classes('w-full max-w-6xl mx-auto items-center justify-between p-2'):
            # Logo
            ui.link('AtleticaDB', '/').classes('text-xl font-bold text-blue-400 no-underline')
            
            # Search
            with ui.row().classes('items-center gap-2'):
                search_input = ui.input(placeholder='Cerca un atleta...').classes('w-64')
                search_results = ui.menu().classes('w-64')
                
                async def on_search(e):
                    query = e.value
                    search_results.clear()
                    
                    if len(query) >= 3:
                        athletes = search_athletes(query, limit=5)
                        societies = search_societies(query, limit=3)
                        
                        with search_results:
                            if athletes:
                                ui.label('Atleti').classes('text-xs text-gray-500 px-2 pt-2')
                                for a in athletes:
                                    link = a.get('link', '').split('/')[-2:] if a.get('link') else []
                                    link_id = '_'.join(link)[:-3] + '=' if link else ''
                                    with ui.menu_item(on_click=lambda l=link_id: ui.navigate.to(f'/atleta/{l}')):
                                        ui.label(f"👤 {a['name']}").classes('text-sm')
                                        if a.get('anno'):
                                            ui.label(f"({a['anno']})").classes('text-xs text-gray-500')
                            
                            if societies:
                                ui.label('Società').classes('text-xs text-gray-500 px-2 pt-2')
                                for s in societies:
                                    with ui.menu_item(on_click=lambda c=s['codice']: ui.navigate.to(f'/societa/{c}')):
                                        ui.label(f"🏢 {s['name']}").classes('text-sm')
                                        ui.label(f"({s['codice']})").classes('text-xs text-gray-500')
                            
                            if not athletes and not societies:
                                ui.label('Nessun risultato').classes('text-sm text-gray-500 p-2')
                        
                        search_results.open()
                    else:
                        search_results.close()
                
                search_input.on('input', on_search)
            
            # Nav links
            with ui.row().classes('gap-4'):
                ui.link('Home', '/').classes('text-gray-300 no-underline hover:text-white')
                ui.link('Rankings', '/rankings').classes('text-gray-300 no-underline hover:text-white')
