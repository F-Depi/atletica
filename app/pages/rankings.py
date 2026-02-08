from nicegui import ui
from components.header import create_header
from database import get_rankings, format_time, should_show_wind
from config import DISCIPLINES, DISCIPLINE_STANDARD, CATEGORIES, REGIONI, CATEGORY_MAPPING


def get_disciplines_for_category(category: str, gender: str) -> list[dict]:
    """Ritorna le discipline disponibili per categoria e genere da DISCIPLINE_STANDARD"""
    if category not in DISCIPLINE_STANDARD:
        return []
    
    disciplines = [
        d for d in DISCIPLINE_STANDARD[category]
        if gender in d.get('sesso', 'MF')
    ]
    return disciplines


def get_discipline_info_from_standard(category: str, discipline: str) -> dict:
    """Ritorna le info della disciplina dal DISCIPLINE_STANDARD"""
    if category not in DISCIPLINE_STANDARD:
        return {}
    
    for d in DISCIPLINE_STANDARD[category]:
        if d['disciplina'] == discipline:
            return d
    return {}


def get_ambiente_options_for_discipline(category: str, discipline: str) -> list[str]:
    """Ritorna le opzioni ambiente disponibili per una disciplina"""
    info = get_discipline_info_from_standard(category, discipline)
    ambiente = info.get('ambiente', 'IP')
    
    # Normalizza
    if ambiente in ['I-P', 'IP']:
        return ['I', 'P', 'IP']
    elif ambiente == 'I':
        return ['I']
    elif ambiente == 'P':
        return ['P']
    else:
        return ['I', 'P', 'IP']


def extract_value(e):
    """Estrae il valore da un evento NiceGUI, gestendo dict, stringhe, ecc."""
    if e is None:
        return None
    
    # Se è un evento con .value
    if hasattr(e, 'value'):
        val = e.value
    # Se è un evento con .args
    elif hasattr(e, 'args'):
        val = e.args
    else:
        val = e
    
    # Se il valore è un dict, estrai il valore
    if isinstance(val, dict):
        return val.get('value') or val.get('label') or val.get('id') or list(val.values())[0] if val else None
    
    return val


@ui.page('/rankings')
def rankings_page():
    create_header()
    
    # Stato dei filtri
    state = {
        'tab': 'men',
        'category': 'ASS',
        'discipline': '60Hs_h106-9.14',
        'ambiente': 'I',
        'year': 2026,
        'regione': '',
        'provincia_societa': '',
        'limit': 50,
        'page': 1,
        'show_all': False,
        'legal_wind_only': True,
        'gender': None,
    }
    
    # Riferimenti ai componenti UI
    ui_refs = {
        'table_container': None,
        'pagination_container': None,
        'discipline_select': None,
        'ambiente_select': None,
        'wind_checkbox_container': None,
        'gender_select': None,
        'category_select': None,
        'year_select': None,
    }
    
    def get_current_gender():
        """Determina il genere in base alla tab corrente"""
        if state['tab'] == 'men':
            return 'M'
        elif state['tab'] == 'women':
            return 'F'
        elif state['tab'] == 'advanced':
            return state.get('gender')
        return None
    
    def update_ambiente_options():
        """Aggiorna le opzioni ambiente in base alla disciplina selezionata"""
        if not ui_refs['ambiente_select']:
            return
        
        if state['tab'] == 'advanced':
            options = ['I', 'P', 'IP']
        else:
            options = get_ambiente_options_for_discipline(state['category'], state['discipline'])
        
        ui_refs['ambiente_select'].options = options
        
        if state['ambiente'] not in options and options:
            state['ambiente'] = options[0]
            ui_refs['ambiente_select'].value = state['ambiente']
        
        ui_refs['ambiente_select'].update()
    
    def update_discipline_options():
        """Aggiorna le opzioni delle discipline in base a categoria e genere"""
        if not ui_refs['discipline_select']:
            return
        
        if state['tab'] == 'advanced':
            options = list(DISCIPLINES.keys())
        else:
            gender = get_current_gender() or 'M'
            disciplines = get_disciplines_for_category(state['category'], gender)
            options = [d['disciplina'] for d in disciplines]
        
        ui_refs['discipline_select'].options = options
        
        if state['discipline'] not in options and options:
            state['discipline'] = options[0]
            ui_refs['discipline_select'].value = state['discipline']
        
        ui_refs['discipline_select'].update()
        update_ambiente_options()
    
    def update_wind_checkbox_visibility():
        """Mostra/nasconde checkbox vento in base alla disciplina e ambiente"""
        if not ui_refs['wind_checkbox_container']:
            return
        
        if state['ambiente'] == 'I':
            ui_refs['wind_checkbox_container'].set_visibility(False)
        else:
            try:
                discipline = state['discipline']
                if discipline and discipline in DISCIPLINES:
                    show = should_show_wind(discipline, state['ambiente'])
                    ui_refs['wind_checkbox_container'].set_visibility(show)
                else:
                    ui_refs['wind_checkbox_container'].set_visibility(False)
            except (KeyError, TypeError):
                ui_refs['wind_checkbox_container'].set_visibility(False)
    
    def load_data():
        """Carica i dati dal database e aggiorna la tabella"""
        gender = get_current_gender()
        ambiente = state['ambiente'] if state['ambiente'] else None
        
        category_to_pass = None
        if state['tab'] in ['men', 'women']:
            category_to_pass = state['category']
        elif state['tab'] == 'advanced' and state['category']:
            category_to_pass = state['category']
        
        discipline = str(state['discipline']) if state['discipline'] else ''
        
        if not discipline or discipline not in DISCIPLINES:
            ui_refs['table_container'].clear()
            with ui_refs['table_container']:
                ui.label(f'Disciplina "{discipline}" non trovata').classes('text-gray-500 p-4')
            ui_refs['pagination_container'].clear()
            return
        
        try:
            results, total_count, total_pages = get_rankings(
                discipline=discipline,
                ambiente=ambiente,
                gender=gender,
                category=category_to_pass,
                year=state['year'] if state['year'] else None,
                regione=state['regione'] if state['regione'] else None,
                provincia_societa=state['provincia_societa'] if state['provincia_societa'] else None,
                limit=state['limit'],
                page=state['page'],
                show_all=state['show_all'],
                legal_wind_only=state['legal_wind_only'],
            )
        except Exception as e:
            ui_refs['table_container'].clear()
            with ui_refs['table_container']:
                ui.label(f'Errore nel caricamento: {str(e)}').classes('text-red-500 p-4')
            ui_refs['pagination_container'].clear()
            return
        
        discipline_info = DISCIPLINES.get(discipline, {})
        show_wind = False
        try:
            if discipline in DISCIPLINES and state['ambiente'] != 'I':
                show_wind = should_show_wind(discipline, state['ambiente'])
        except:
            pass
        
        # Aggiorna tabella
        ui_refs['table_container'].clear()
        with ui_refs['table_container']:
            if not results:
                ui.label('Nessun risultato trovato').classes('text-gray-500 p-4')
            else:
                columns = [
                    {'name': 'position', 'label': '#', 'field': 'position', 'align': 'left', 'sortable': True},
                    {'name': 'prestazione', 'label': 'Risultato', 'field': 'prestazione_fmt', 'align': 'left'},
                ]
                
                if show_wind:
                    columns.append({'name': 'vento', 'label': 'Vento', 'field': 'vento_fmt', 'align': 'left'})
                
                columns.extend([
                    {'name': 'atleta', 'label': 'Atleta', 'field': 'atleta', 'align': 'left'},
                    {'name': 'anno', 'label': 'Anno', 'field': 'anno', 'align': 'left'},
                    {'name': 'categoria', 'label': 'Categoria', 'field': 'categoria', 'align': 'left'},
                    {'name': 'societa', 'label': 'Società', 'field': 'società', 'align': 'left'},
                    {'name': 'luogo', 'label': 'Luogo', 'field': 'luogo', 'align': 'left'},
                    {'name': 'data', 'label': 'Data', 'field': 'data_fmt', 'align': 'left'},
                ])
                
                rows = []
                for r in results:
                    if r.get('ambiente') == 'I':
                        vento_fmt = '(Indoor)'
                    elif r.get('vento') is not None:
                        vento_fmt = f"{r['vento']:+.1f}"
                    else:
                        vento_fmt = '-'
                    
                    row = {
                        **r,
                        'prestazione_fmt': format_time(r['prestazione'], discipline_info, r.get('cronometraggio')),
                        'vento_fmt': vento_fmt,
                        'data_fmt': r['data'].strftime('%d/%m/%Y') if r.get('data') else '',
                    }
                    rows.append(row)
                
                table = ui.table(
                    columns=columns,
                    rows=rows,
                    row_key='position',
                    pagination={'rowsPerPage': 0}
                ).classes('w-full')
                
                table.on('rowClick', lambda e: show_detail_dialog(e.args[1]))
        
        # Aggiorna paginazione
        ui_refs['pagination_container'].clear()
        with ui_refs['pagination_container']:
            with ui.row().classes('items-center justify-between w-full py-4'):
                ui.label(f'{total_count} risultati totali').classes('text-sm text-gray-500')
                
                if total_pages > 1:
                    with ui.row().classes('items-center gap-1'):
                        first_btn = ui.button('«', on_click=lambda: go_to_page(1))
                        first_btn.props('flat dense')
                        if state['page'] == 1:
                            first_btn.props(add='disable')
                        
                        prev_btn = ui.button('‹', on_click=lambda: go_to_page(state['page'] - 1))
                        prev_btn.props('flat dense')
                        if state['page'] == 1:
                            prev_btn.props(add='disable')
                        
                        start = max(1, state['page'] - 2)
                        end = min(total_pages, state['page'] + 2)
                        
                        if start > 1:
                            ui.label('...').classes('px-2')
                        
                        for p in range(start, end + 1):
                            btn = ui.button(str(p), on_click=lambda p=p: go_to_page(p))
                            if p == state['page']:
                                btn.props('color=primary')
                            else:
                                btn.props('flat dense')
                        
                        if end < total_pages:
                            ui.label('...').classes('px-2')
                        
                        next_btn = ui.button('›', on_click=lambda: go_to_page(state['page'] + 1))
                        next_btn.props('flat dense')
                        if state['page'] == total_pages:
                            next_btn.props(add='disable')
                        
                        last_btn = ui.button('»', on_click=lambda: go_to_page(total_pages))
                        last_btn.props('flat dense')
                        if state['page'] == total_pages:
                            last_btn.props(add='disable')
                        
                        ui.label('|').classes('text-gray-400 mx-2')
                        page_input = ui.number(
                            value=state['page'], 
                            min=1, 
                            max=total_pages,
                            step=1
                        ).classes('w-20').props('dense')
                        ui.button('Vai', on_click=lambda: go_to_page(int(page_input.value))).props('dense')
    
    def go_to_page(page: int):
        """Vai a una pagina specifica"""
        state['page'] = max(1, page)
        load_data()
    
    def show_detail_dialog(row):
        """Mostra dialog con dettagli del risultato"""
        discipline = str(state['discipline']) if state['discipline'] else ''
        
        with ui.dialog() as dialog, ui.card().classes('min-w-96'):
            discipline_info = DISCIPLINES.get(discipline, {})
            prestazione_fmt = format_time(row['prestazione'], discipline_info, row.get('cronometraggio'))
            
            ui.label(f"{row['atleta']}").classes('text-xl font-bold')
            ui.label(f"{prestazione_fmt} (#{row['position']})").classes('text-lg text-primary')
            
            ui.separator()
            
            with ui.column().classes('gap-2'):
                ui.label(f"📅 Data: {row.get('data_fmt', '-')}")
                ui.label(f"📍 Luogo: {row.get('luogo', '-')}")
                ui.label(f"🏃 Categoria: {row.get('categoria', '-')}")
                ui.label(f"🏢 Società: {row.get('società', '-')}")
                if row.get('vento') is not None and row.get('ambiente') == 'P':
                    ui.label(f"💨 Vento: {row['vento']:+.1f} m/s")
            
            ui.separator()
            
            if row.get('link_atleta'):
                parts = row['link_atleta'].split('/')
                if len(parts) >= 2:
                    link_id = '_'.join(parts[-2:])[:-3] + '='
                    ui.button(
                        '👤 Profilo atleta', 
                        on_click=lambda: ui.navigate.to(f'/atleta/{link_id}')
                    ).classes('w-full')
            
            if row.get('cod_società'):
                ui.button(
                    f"🏢 Pagina società ({row['cod_società']})",
                    on_click=lambda: ui.navigate.to(f'/societa/{row["cod_società"]}')
                ).classes('w-full')
            
            ui.separator()
            
            with ui.expansion('🚨 Segnala errore', icon='report').classes('w-full'):
                error_text = ui.textarea(placeholder='Descrivi l\'errore...').classes('w-full')
                
                def send_report():
                    if error_text.value:
                        ui.notify('Segnalazione inviata!', type='positive')
                        dialog.close()
                    else:
                        ui.notify('Inserisci una descrizione', type='warning')
                
                ui.button('Invia segnalazione', on_click=send_report, color='red').classes('w-full mt-2')
            
            ui.button('Chiudi', on_click=dialog.close).props('flat').classes('w-full mt-4')
        
        dialog.open()
    
    def on_tab_change(new_tab):
        """Gestisce cambio tab"""
        state['tab'] = new_tab
        state['page'] = 1
        
        if new_tab in ['men', 'women']:
            state['gender'] = None
        
        update_discipline_options()
        update_wind_checkbox_visibility()
        update_gender_visibility()
        load_data()
    
    def update_gender_visibility():
        """Mostra/nasconde selettore genere in base alla tab"""
        if ui_refs['gender_select']:
            ui_refs['gender_select'].set_visibility(state['tab'] == 'advanced')
    
    # === Handler per i filtri ===
    
    def handle_category_change(e):
        value = extract_value(e)
        if value:
            state['category'] = str(value)
            state['page'] = 1
            update_discipline_options()
            load_data()
    
    def handle_discipline_change(e):
        value = extract_value(e)
        if value:
            state['discipline'] = str(value)
            state['page'] = 1
            update_ambiente_options()
            update_wind_checkbox_visibility()
            load_data()
    
    def handle_ambiente_change(e):
        value = extract_value(e)
        if value:
            state['ambiente'] = str(value)
            state['page'] = 1
            update_wind_checkbox_visibility()
            load_data()
    
    def handle_year_change(e):
        value = extract_value(e)
        if value is None or value == '':
            state['year'] = None
        else:
            try:
                state['year'] = int(value)
            except (ValueError, TypeError):
                state['year'] = None
        state['page'] = 1
        load_data()
    
    def handle_regione_change(e):
        value = extract_value(e)
        state['regione'] = str(value) if value else ''
        state['page'] = 1
        load_data()
    
    def handle_limit_change(e):
        value = extract_value(e)
        if value:
            try:
                state['limit'] = int(value)
            except (ValueError, TypeError):
                state['limit'] = 50
        state['page'] = 1
        load_data()
    
    def handle_gender_change(e):
        value = extract_value(e)
        state['gender'] = str(value) if value else None
        state['page'] = 1
        load_data()
    
    def handle_show_all_change(e):
        value = extract_value(e)
        state['show_all'] = bool(value)
        state['page'] = 1
        load_data()
    
    def handle_legal_wind_change(e):
        value = extract_value(e)
        state['legal_wind_only'] = bool(value)
        state['page'] = 1
        load_data()
    
    def handle_provincia_change(e):
        value = extract_value(e)
        state['provincia_societa'] = str(value).upper() if value else ''
    
    def handle_provincia_search():
        """Esegue la ricerca quando si preme invio o si clicca cerca"""
        state['page'] = 1
        load_data()
    
    # === COSTRUZIONE UI ===
    
    with ui.column().classes('w-full max-w-7xl mx-auto p-4 gap-4'):
        
        # === TABS ===
        with ui.tabs().classes('w-full') as tabs:
            ui.tab('men', label='Uomini')
            ui.tab('women', label='Donne')
            ui.tab('advanced', label='Tutti i filtri')
        
        tabs.on_value_change(lambda e: on_tab_change(e.value))
        
        # === FILTRI ===
        with ui.card().classes('w-full'):
            with ui.row().classes('w-full flex-wrap gap-4 items-end'):
                
                # Genere (solo per tab advanced)
                gender_select = ui.select(
                    options=['', 'M', 'F'],
                    value=state.get('gender') or '',
                    label='Genere'
                ).classes('w-28')
                gender_select.on_value_change(handle_gender_change)
                gender_select.set_visibility(False)
                ui_refs['gender_select'] = gender_select
                
                # Categoria
                category_options = [c[0] for c in CATEGORIES]
                category_select = ui.select(
                    options=category_options,
                    value=state['category'],
                    label='Categoria'
                ).classes('w-32')
                category_select.on_value_change(handle_category_change)
                ui_refs['category_select'] = category_select
                
                # Disciplina
                initial_disciplines = get_disciplines_for_category(state['category'], 'M')
                discipline_options = [d['disciplina'] for d in initial_disciplines]
                discipline_select = ui.select(
                    options=discipline_options,
                    value=state['discipline'],
                    label='Disciplina'
                ).classes('w-48')
                discipline_select.on_value_change(handle_discipline_change)
                ui_refs['discipline_select'] = discipline_select
                
                # Ambiente
                initial_ambiente_options = get_ambiente_options_for_discipline(state['category'], state['discipline'])
                ambiente_select = ui.select(
                    options=initial_ambiente_options,
                    value=state['ambiente'],
                    label='Ambiente'
                ).classes('w-28')
                ambiente_select.on_value_change(handle_ambiente_change)
                ui_refs['ambiente_select'] = ambiente_select
                
                # Anno
                year_options = [''] + [str(y) for y in range(2026, 2004, -1)]
                year_select = ui.select(
                    options=year_options,
                    value=str(state['year']) if state['year'] else '', 
                    label='Anno'
                ).classes('w-28')
                year_select.on_value_change(handle_year_change)
                ui_refs['year_select'] = year_select
                
                # Regione
                regione_options = [r[0] for r in REGIONI]
                regione_select = ui.select(
                    options=regione_options,
                    value=state['regione'],
                    label='Regione'
                ).classes('w-44')
                regione_select.on_value_change(handle_regione_change)
                
                # Provincia/Società
                provincia_input = ui.input(
                    label='Provincia/Società',
                    placeholder='es: RM o RM052',
                    value=state['provincia_societa']
                ).classes('w-32')
                provincia_input.on_value_change(handle_provincia_change)
                provincia_input.on('keydown.enter', lambda: handle_provincia_search())
                
                # Numero risultati per pagina
                limit_options = [50, 100, 200, 500]
                limit_select = ui.select(
                    options=limit_options,
                    value=state['limit'],
                    label='Per pagina'
                ).classes('w-24')
                limit_select.on_value_change(handle_limit_change)
        
        # === OPZIONI AGGIUNTIVE ===
        with ui.row().classes('items-center gap-6 flex-wrap'):
            all_results_switch = ui.switch('Mostra tutti i risultati', value=state['show_all'])
            all_results_switch.on_value_change(handle_show_all_change)
            all_results_switch.tooltip('Se attivo mostra tutte le prestazioni, altrimenti solo la migliore per atleta')
            
            wind_checkbox_container = ui.row().classes('items-center')
            with wind_checkbox_container:
                wind_check = ui.checkbox('Solo vento regolare (≤ +2.0)', value=state['legal_wind_only'])
                wind_check.on_value_change(handle_legal_wind_change)
            ui_refs['wind_checkbox_container'] = wind_checkbox_container
            update_wind_checkbox_visibility()
            
            ui.button('Applica', on_click=load_data, color='primary').props('unelevated')
        
        ui.separator()
        
        # === TABELLA RISULTATI ===
        ui_refs['table_container'] = ui.column().classes('w-full')
        
        # === PAGINAZIONE ===
        ui_refs['pagination_container'] = ui.row().classes('w-full')
        
        # Carica dati iniziali
        load_data()
