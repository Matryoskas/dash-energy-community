from dash import Dash, html, dcc, callback, Output, Input, State, ctx, ALL
from dash.exceptions import PreventUpdate
import dash_deck
import os
import json
import dash_bootstrap_components as dbc
from algorithm import algorithm, create_map

# Get your Mapbox API token from the environment
mapbox_api_token = os.getenv("MAPBOX_ACCESS_TOKEN")
# Create the initial map (without any building selection)
map_initial = create_map()

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
# Define the layout for the "Map" page.
# ------------------------------
layout_map = dbc.Container([
    dcc.Store(id='buildings-info-store'),
    dcc.Store(id='save-status-store', data={'status': 'idle'}),
    html.Br(),
    html.H1("Mapa e Controlos", style={'textAlign': 'center'}),
    html.Br(),
    html.P(
        "Seleciona os edifícios para participar na comunidade de energia, escolhe "
        "a capacidade da bateria e o método para distribuir o excedente solar.",
        style={'textAlign': 'center', 'fontSize': '20px'}
    ),
    html.Br(),
    dbc.Row([
        dbc.Col([
            html.P("Distribuição do excedente solar", style={'fontSize': '20px'}),
            dcc.Dropdown(
                ['By Demand', 'By Electricity Production'],
                'By Demand',
                id='dropdown',
                clearable=False
            ),
            html.Br(),
            html.P(
                "Capacidade da Bateria (1 = 1x a média diária de consumo)",
                style={'fontSize': '20px'}
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
                    map_initial,
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
        ], width=6),
        dbc.Col([
            dcc.Loading(type='graph', children=dcc.Graph(id='2d-map')),
            dbc.Card([dbc.CardHeader(id='building-details-title', children="Building Details"),
            dbc.CardBody(
                id='building-customization-fields',
                children=[],  # Dynamically populated
            )],
            id='building-details-card',
            style={"display": "none", "position": "fixed", "top": "10%", "right": "5%", "width": "25%"}
            )
        ], width=4)
    ])
], fluid=True)

# ------------------------------
# Define the layout for the "Data Analysis" page.
# ------------------------------
layout_analysis = dbc.Container([
    html.Br(),
    html.H1("Análise de Dados", style={'textAlign': 'center'}),
    html.Br(),
    html.P(
        "As seguintes figuras mostram os indicadores de performance: "
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

# ------------------------------
# Define the main app layout with a Navbar and a Location component.
# ------------------------------
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dcc.Link("Mapa", href="/map", className="nav-link")),
            dbc.NavItem(dcc.Link("Análise de Dados", href="/analysis", className="nav-link"))
        ],
        brand="Comunidade de Energia",
        color="primary",
        dark=True,
        sticky="top"
    ),
    # A hidden Store component to hold the analysis figures (so they can be shared across pages)
    dcc.Store(id='analysis-data'),
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
    # Default page (or if pathname == '/map')
    return layout_map

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
    Output('2d-map', 'figure'),
    Output('analysis-data', 'data'),
    Output('dropdown', 'value'),
    State('battery-efficiency', 'value'),
    State('dropdown', 'value'),
    Input('run-button', 'n_clicks'),
    Input('reset-button', 'n_clicks'),
    State('buildings-info-store', 'data'),
    prevent_initial_call=True
)
def update_map(batt_eff, current_dropdown, run_button, reset_button, buildings_update):
    # When reset is triggered, clear selections and revert to defaults
    if ctx.triggered_id == 'reset-button':
        print('Resetting...')
        # Clear any building outlines (this attribute is stored on the update_building_outlines function)
        update_building_outlines.outlined_buildings = []
        # Call your algorithm without building selections
        map3d_data, map2d_data, cons_fig, sav_fig, pv_fig = algorithm()
        analysis_data = {
            'consumption': cons_fig,
            'savings': sav_fig,
            'pv': pv_fig
        }
        return map3d_data, map2d_data, analysis_data, 'By Demand'
    else:
        # When running the algorithm normally, use the current building selections.
        outlined_buildings = getattr(update_building_outlines, 'outlined_buildings', [])
        print("Buildings selected:", outlined_buildings)
        map3d_data, map2d_data, cons_fig, sav_fig, pv_fig = algorithm(outlined_buildings, current_dropdown, batt_eff, buildings_update)
        analysis_data = {
            'consumption': cons_fig,
            'savings': sav_fig,
            'pv': pv_fig
        }
        return map3d_data, map2d_data, analysis_data, current_dropdown

@callback(
    Output('3d-map', 'data', allow_duplicate=True),
    Input('3d-map', 'clickInfo'),
    State('3d-map', 'data'),
    prevent_initial_call=True
)
def update_building_outlines(click_info, previous_data):
    # Track selected buildings using a hidden state
    outlined_buildings = getattr(update_building_outlines, 'outlined_buildings', [])

    if click_info is not None:
        clicked_building = click_info.get('object', {}).get('Name', None)
        print('clicked building: ', clicked_building)
        if clicked_building:
            if clicked_building in outlined_buildings:
                # If building is already selected, deselect it
                outlined_buildings.remove(clicked_building)
            else:
                # Add clicked building to the selection
                outlined_buildings.append(clicked_building)
    # Store selected buildings back to the hidden state
    update_building_outlines.outlined_buildings = outlined_buildings
    
    print('outlined buildings: ', outlined_buildings)

    previous_data = json.loads(previous_data)

    # Ensure the layers are correctly accessed
    layers = previous_data.get("layers", [])
    
    # Extract the current extruded layer from the existing layers
    extruded_layer = next(layer for layer in layers if layer['id'] == "extruded-layer")

    result = create_map(outlined_buildings=outlined_buildings, previous_layer=extruded_layer)
    return result

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
