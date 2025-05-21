from dash import Dash, html, dcc, callback, Output, Input, State, ctx, ALL
from dash.exceptions import PreventUpdate
import dash_deck
import os
import json
import dash_bootstrap_components as dbc
from algorithm import algorithm, create3d_map, create_2d_map

# Get your Mapbox API token from the environment
mapbox_api_token = os.getenv("MAPBOX_ACCESS_TOKEN")
# Create the initial map (without any building selection)
map3d_initial = create3d_map()
map2d_initial = create_2d_map()

# Initialize the app with a Bootstrap stylesheet
app = Dash(__name__, external_stylesheets=[dbc.themes.MINTY])
app.title = "Comunidade de Energia"

# Tooltip configuration for the map
tooltip = {
    "html": (
        "<b>Building:</b> {Name} <br />"
        "<b>Ecost_base (€):</b> {Ecost_base (€)} <br />"
        "<b>Ecost_SC (€):</b> {Ecost_SC (€)} <br />"
        "<b>Ecost_EC_BESS (€):</b> {Ecost_EC_BESS (€)}"
    )
}

# ------------------------------
# Define the layout for the "Characterization" page.
# ------------------------------
layout_characterization = dbc.Container([
        
    dbc.Row([
        html.H5("Caracterização dos edifícios", style={"fontWeight": "bold"}),
        html.P(
            "No mapa da direita é possível caracterizar os edifícios relativamente à área de PV em % da área de cobertura disponível "
            "e ao número de carros eléctricos. Pode seleccionar os edifícios a caracterizar usando a ferramenta Lasso ou Box no canto "
            "superior do mapa. Ao seleccionar, aparece um quadro com os edifícios seleccionados."
        ),
    ]),
    dbc.Row([
        dcc.Loading(type='graph', children=dcc.Graph(figure=map2d_initial, id='2d-map')),
        dbc.Card([dbc.CardHeader(id='building-details-title', children="Building Details"),
        dbc.CardBody(
            id='building-customization-fields',
            children=[],  # Dynamically populated
        )],
        id='building-details-card',
        style={"display": "none", "position": "fixed", "top": "10%", "right": "5%", "width": "25%"}
        )
    ])
])

# ------------------------------
# Define the layout for the "Map" page.
# ------------------------------
layout_map = dbc.Container([
    html.Br(),
    html.H1("Comunidade de Energia", style={'textAlign': 'center'}),
    html.Br(),
    dbc.Row([
        dbc.Col([
            html.H5("Seleção de edifícios", style={"fontWeight": "bold"}),
            html.P(
                "No mapa da esquerda é possível seleccionar quais os edifícios participantes de uma comunidade de energia. "
                "Pode seleccionar um edifício individualmente e, utilizando a tecla Ctrl, é possível seleccionar vários edifícios. "
                "A distribuição do excedente solar de produção de electricidade tem duas opções:"
            ),
            html.Ul([
                html.Li("By demand - rasteio horário de acordo com o consumo de electricidade dos edifícios participantes."),
                html.Li("Electricity Production - rateio horário segundo a produção anual estimada de PV.")
            ]),
            html.P(
                "O dimensionamento da capacidade da bateria é calculado por: n x consumo médio diário dos edifícios participantes."
            ),
        ]),

    ]),
    html.Br(),

    
    dbc.Row([
        dbc.Col([
            html.P("Distribuição do excedente solar", style={'fontSize': '20px', 'color': '#009FE3'}),
            dcc.Dropdown(
                ['By Demand', 'By Electricity Production'],
                'By Demand',
                id='dropdown',
                clearable=False
            ),
            html.Br(),
            html.P(
                "Capacidade da Bateria (1 = 1x a média diária de consumo)",
                style={'fontSize': '20px','color': '#009FE3'}
            ),
            dcc.Input(
                id='battery-efficiency',
                type='number',
                value=1,
                min=0,
                max=1,
                step=0.1,
                placeholder='Eficiência da bateria'
            ),
            html.Br(),
            html.Br(),
            dcc.Loading(
                type='default',
                children=dash_deck.DeckGL(
                    map3d_initial,
                    id="3d-map",
                    mapboxKey=mapbox_api_token,
                    tooltip=tooltip,
                    enableEvents=['click'],
                    style={"width": "100%", "height": "60vh", "position": "relative", "zIndex": "0"}
                )
            ),
            dbc.Button('Correr algoritmo', color="primary", id='run-button'),
            html.Span("    "),
            dbc.Button('Reset', color="secondary", id='reset-button'),
        ]),
    ])
], fluid=True)

# ------------------------------
# Define the layout for the "Data Analysis" page.
# ------------------------------
layout_analysis = dbc.Container([
    html.Br(),
    html.H1("Análise de Resultados", style={'textAlign': 'center'}),
    html.Br(),
    html.P(
        "As seguintes figuras mostram os indicadores de performance da comunidade de energia seleccionada: "
        "self-consumption, self-sufficiency, annual electricity cost (€), "
        "PV power (W) e investment (€).",
        style={'textAlign': 'center', 'fontSize': '20px'}
    ),
    html.Br(),
    dbc.Row([
        dbc.Col(
            dcc.Loading(type='default', children=dcc.Graph(id='savings-figure')),
            width=12
        )
    ]),
    html.Br(),
    dbc.Row([
        dbc.Col(
            dcc.Loading(type='default', children=dcc.Graph(id='PV-figure')),
        ),
        dbc.Col(
           dcc.Loading(type='default', children=dcc.Graph(id='consumption-figure')),
        )
    ])
], fluid=True)


# Página inicial com explicação
layout_intro = dbc.Container([
    html.Br(),
    html.H1("Bem-vindo ao Dashboard da Comunidade de Energia", style={'textAlign': 'center'}),
    html.Br(),
    html.P(
        "Este dashboard permite avaliar a performance de comunidade de energia (electricidade) de uma área urbana. "
        "O dashboard tem três páginas: \"Caracterização\", \"Mapas\" e \"Análise de Resultados\".",
        style={'textAlign': 'center', 'fontSize': '20px'}
    ),
    html.Br(),
    html.Div(
        dbc.Button("Entrar no Dashboard", color="primary", href="/characterization", size="lg"),
        style={'textAlign': 'center'}
    )
], fluid=True)

# ------------------------------
# Define the main app layout with a Navbar and a Location component.
# ------------------------------
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dcc.Link("Caracterização", href="/characterization", className="nav-link")),
            dbc.NavItem(dcc.Link("Mapa", href="/map", className="nav-link")),
            dbc.NavItem(dcc.Link("Análise de Resultados", href="/analysis", className="nav-link"))
        ],
        color="primary",
        dark=True,
        sticky="top"
    ),
    dcc.Store(id='analysis-data'),
    dcc.Store(id='buildings-info-store'),
    dcc.Store(id='outlined-buildings-store', data=[]),
    dcc.Store(id='save-status-store', data={'status': 'idle'}),
    html.Div(id='page-content')
])

# ------------------------------
# Callback to route between pages
# ------------------------------
@callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/analysis':
        return layout_analysis
    elif pathname == '/map':
        return layout_map
    elif pathname == '/characterization':
        return layout_characterization
    # Página inicial
    return layout_intro

# ------------------------------
# Map page callbacks
# ------------------------------

# ------------------------------
# Callback to update the map and run the algorithm.
#
# This callback is triggered by the "Run Algorithm" or "Reset" buttons.
# It outputs:
#   - Updated data for the 3D map (Deck.GL)
#   - A dictionary containing the three analysis figures stored in 'analysis-data'
#   - The current value of the dropdown (for consistency)
# ------------------------------
@callback(
    Output('3d-map', 'data'),
    Output('analysis-data', 'data'),
    Output('dropdown', 'value'),
    State('battery-efficiency', 'value'),
    State('dropdown', 'value'),
    State('outlined-buildings-store', 'data'),
    State('buildings-info-store', 'data'),
    Input('run-button', 'n_clicks'),
    Input('reset-button', 'n_clicks'),
    prevent_initial_call=True
)
def update_map(batt_eff, current_dropdown, outlined_buildings, buildings_update, run_clicks, reset_clicks):
    if (run_clicks is None or run_clicks == 0) and (reset_clicks is None or reset_clicks == 0):
        raise PreventUpdate

    if ctx.triggered_id == 'reset-button':
        map3d_data, cons_fig, sav_fig, pv_fig = algorithm()
        analysis_data = {
            'consumption': cons_fig,
            'savings': sav_fig,
            'pv': pv_fig
        }
        return map3d_data, analysis_data, 'By Demand'

    if ctx.triggered_id == 'run-button':
        map3d_data, cons_fig, sav_fig, pv_fig = algorithm(
            outlined_buildings,
            current_dropdown,
            batt_eff,
            buildings_update
        )
        analysis_data = {
            'consumption': cons_fig,
            'savings': sav_fig,
            'pv': pv_fig
        }
        return map3d_data, analysis_data, current_dropdown

    raise PreventUpdate


@callback(
    Output('outlined-buildings-store', 'data'),
    Input('3d-map', 'clickInfo'),
    State('outlined-buildings-store', 'data'),
    prevent_initial_call=True
)
def update_outlined_buildings(click_info, current_outlined):
    if current_outlined is None:
        current_outlined = []

    if click_info is not None:
        clicked_building = click_info.get('object', {}).get('Name', None)
        if clicked_building:
            if clicked_building in current_outlined:
                current_outlined.remove(clicked_building)
            else:
                current_outlined.append(clicked_building)

    return current_outlined

@callback(
    Output('3d-map', 'data', allow_duplicate=True),
    Input('outlined-buildings-store', 'data'),
    State('3d-map', 'data'),
    prevent_initial_call=True
)
def render_outlined_buildings(outlined_buildings, previous_data):
    previous_data = json.loads(previous_data)
    extruded_layer = next(layer for layer in previous_data.get("layers", []) if layer['id'] == "extruded-layer")
    return create3d_map(outlined_buildings=outlined_buildings, previous_layer=extruded_layer)

# ------------------------------
# Characterization page callbacks
# ------------------------------

@callback(
    Output('building-details-card', 'style'),  # Control card visibility
    Output('building-details-title', 'children'),  # Title for the card
    Output('building-customization-fields', 'children'),  # Fields inside the card
    Input('2d-map', 'selectedData'),  # Detect clicks on the 2D map
    State('building-details-card', 'style'),  # Card visibility
    State('buildings-info-store', 'data')  # Get stored building data
)
def show_building_customization(selected_data, card_style, stored_data):
    # If a building is clicked
    if selected_data and selected_data.get("points"):
        # Convert stored data to a dictionary for easier lookup
        data_dict = {building['building_name']: building for building in (stored_data or [])}

        fields = [dbc.Row([
            dbc.Col(),
            dbc.Col(html.Label("% de área de cobertura com PV")),
            dbc.Col(html.Label("Número de veículos elétricos"))
        ])]

        for i, point in enumerate(selected_data["points"]):
            building_info = point.get("customdata", {})
            building_name = next((x for x in building_info if isinstance(x, str)), None)

            # Check if building data exists in stored data
            default_pv = data_dict.get(building_name, {}).get('area_coverage_pv', 100)
            default_ev = data_dict.get(building_name, {}).get('ev_charging', 0)

            # Populate the customization fields with building information
            fields.append(
                dbc.Row([
                    dbc.Col(html.Label(building_name), id={'type': 'building-name', 'index': i}),
                    dbc.Col(dbc.Input(
                        type="number",
                        min=0,
                        max=100,
                        id={'type': 'building-pv-input', 'index': i},
                        value=default_pv
                    )),
                    dbc.Col(dbc.Input(
                        type="number",
                        min=0,
                        id={'type': 'building-ev-select', 'index': i}, 
                        value=default_ev
                    ))
                ])
            )

        # Add save changes button to the end
        fields.append(dbc.Button("Save Changes", id="save-buildings-customization", color="primary"))

        # Make card visible and populate with fields
        return {"display": "block"}, "Edifícios Selecionados", fields

    # Hide the card if no building is clicked
    return {"display": "none"}, "", []

@callback(
    Output('buildings-info-store', 'data'),
    Output('save-status-store', 'data'),
    Input('save-buildings-customization', 'n_clicks'),
    State('buildings-info-store', 'data'),
    State({'type': 'building-name', 'index': ALL}, 'children'),
    State({'type': 'building-pv-input', 'index': ALL}, 'value'),
    State({'type': 'building-ev-select', 'index': ALL}, 'value'),
    prevent_initial_call=True
)
def save_building_info(n_clicks, existing_data, building_names, pv_values, ev_values):
    if not n_clicks:
        raise PreventUpdate

    # Initialize storage if it does not exist
    if existing_data is None:
        existing_data = []

    # Create a dictionary for easier lookup
    data_dict = {building['building_name']: building for building in existing_data}

    # Define default values
    default_pv = 100
    default_ev = 0

    # Update or add buildings
    for name, pv, ev in zip(building_names, pv_values, ev_values):
        # Extract the label text from the children property
        if isinstance(name, dict) and 'props' in name and 'children' in name['props']:
            name = name['props']['children']

        # If the building already exists, update it
        if name in data_dict:
            data_dict[name]['area_coverage_pv'] = pv
            data_dict[name]['ev_charging'] = ev
        else:
            # Only add new buildings if their values are not default
            if pv != default_pv or ev != default_ev:
                data_dict[name] = {
                    'building_name': name,
                    'area_coverage_pv': pv,
                    'ev_charging': ev
                }

    # Convert back to a list and return
    updated_data = list(data_dict.values())
    print("Updated Buildings Data:", updated_data)
    return updated_data, {'status': 'saved'}

@callback(
    Output('save-buildings-customization', 'children'),
    Input('save-status-store', 'data'),
    prevent_initial_call=True
)
def update_save_button_text(save_status):
    if save_status['status'] == 'saved':
        # Return "Saved!" with a checkmark
        return html.Span(["✔ Saved!"])
    # Default text
    return "Save Changes"

@callback(
    Output('save-status-store', 'data', allow_duplicate=True),
    Input('save-status-store', 'data'),
    prevent_initial_call=True
)
def reset_save_status(save_status):
    if save_status['status'] == 'saved':
        import time
        time.sleep(2)  # Wait for 2 seconds before resetting
        return {'status': 'idle'}
    return save_status

# ------------------------------
# Callbacks to update the figures on the Data Analysis page by reading from the stored analysis data.
# ------------------------------
@callback(
    Output('consumption-figure', 'figure'),
    Input('analysis-data', 'data')
)
def update_consumption_figure(analysis_data):
    if analysis_data is None:
        return {}
    return analysis_data.get('consumption', {})

@callback(
    Output('savings-figure', 'figure'),
    Input('analysis-data', 'data')
)
def update_savings_figure(analysis_data):
    if analysis_data is None:
        return {}
    return analysis_data.get('savings', {})

@callback(
    Output('PV-figure', 'figure'),
    Input('analysis-data', 'data')
)
def update_PV_figure(analysis_data):
    if analysis_data is None:
        return {}
    return analysis_data.get('pv', {})

if __name__ == '__main__':
    app.run(debug=True)