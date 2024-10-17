from dash import Dash, html, dcc, callback, Output, Input, State, ctx
import dash_deck
import os
import json
import dash_bootstrap_components as dbc
from algorithm import algorithm, create_map

mapbox_api_token = os.getenv("MAPBOX_ACCESS_TOKEN")
map = create_map()

app = Dash(__name__, external_stylesheets=[dbc.themes.MINTY])

tooltip = {"html": "<b>Building:</b> {Name} <br /><b>Ecost_base (€):</b> {Ecost_base (€)} <br /><b>Ecost_SC (€):</b> {Ecost_SC (€)} <br /><b>Ecost_EC_BESS (€):</b> {Ecost_EC_BESS (€)}"}

app.layout = dbc.Container([
    html.H1(children='Energy community - neighborhood in Viana do Castelo', style={'textAlign': 'center'}),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            dbc.Row(dcc.Input(id='battery-efficiency', type='number', value=1, min=0, max=1, step=0.1, placeholder='Eficiência da bateria')),
            html.Br(),
            dbc.Row(dcc.Dropdown(['By Demand', 'By Electricity Production'], 'By Demand', id='dropdown')),
            html.Br(),
            dbc.Row(dcc.Loading(type='graph',
                                children=dash_deck.DeckGL(
                                    map, 
                                    id="3d-map", 
                                    mapboxKey=mapbox_api_token, 
                                    tooltip=tooltip, 
                                    enableEvents=['click'], 
                                    style={"width": "45vw", "height": "60vh", "position": "relative", "zIndex": "0"}
                                ))),
            html.Br(),
            dbc.Row([
                dbc.Col(html.Button('Run Algorithm', id='run-button')),
                dbc.Col(html.Button('Reset', id='reset-button')),
            ]),

        ]),
        dbc.Col([
            dbc.Row(dcc.Loading(type='graph',
                                children=dcc.Graph(id='consumption-figure'))),
            dbc.Row(dcc.Loading(type='graph',
                                children=dcc.Graph(id='savings-figure'))),
        ])
    ])
], fluid=True)

@callback(
    Output('3d-map', 'data'),
    Output('consumption-figure', 'figure'),
    Output('savings-figure', 'figure'),
    Output('dropdown', 'value'),
    State('battery-efficiency', 'value'),
    State('dropdown', 'value'),
    Input('run-button', 'n_clicks'),
    Input('reset-button', 'n_clicks')
)
def update_map(batt_eff, value, run_button, reset_button):
    if (ctx.triggered_id == 'reset-button'):
        print('reset')
        return algorithm() + ('By Demand',)

    print('update')
    outlined_buildings = getattr(update_building_outlines, 'outlined_buildings', [])
    print(outlined_buildings)
    return algorithm(outlined_buildings, value, batt_eff)+ (value,)

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

if __name__ == '__main__':
    app.run(debug=True)
