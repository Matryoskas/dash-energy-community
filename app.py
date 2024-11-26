from dash import Dash, html, dcc, callback, Output, Input, State, ctx
import dash_deck
import os
import json
import dash_bootstrap_components as dbc
from algorithm import algorithm, create_map

mapbox_api_token = os.getenv("MAPBOX_ACCESS_TOKEN")
map = create_map()

app = Dash(__name__, 
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1.0"}],
    external_stylesheets=[dbc.themes.MINTY])

tooltip = {"html": "<b>Building:</b> {Name} <br /><b>Ecost_base (€):</b> {Ecost_base (€)} <br /><b>Ecost_SC (€):</b> {Ecost_SC (€)} <br /><b>Ecost_EC_BESS (€):</b> {Ecost_EC_BESS (€)}"}

app.layout = dbc.Container([
    html.Br(),
    html.H1(children='Comunidade de Energia - análise de um bairro em Viana do Castelo', style={'textAlign': 'center'}),
    html.Br(),
    html.P("Dashboard que permite seleccionar um conjunto de edifícios participantes de uma Comunidade de Energia (CE) apresentando indicadores sobre a sua performance.",
        style={'textAlign': 'left', 'fontSize': '25px'}),
    html.P("No mapa seleccione os edifícios participantes de uma comunidade de energia. Poderá seleccionar a capacidade de armazenamento do sistema de bateria e o método de distribuição do excedent de produção de electricidade por PV.",
        style={'textAlign': 'left', 'fontSize': '25px'}),
    html.P("A capacidade da bateria varia entre 0-1, sendo que 1 corresponde a um dia de consumo médio da comunidade seleccionada. O excedente no momento i poderá ser distribuido por: 'Demand' consumo de energia dos edíficios participantes da comunidade no momento i ou 'Electricity production' pela electricidade produzida anualmente por participante.",
        style={'textAlign': 'left', 'fontSize': '25px'}),
    html.P("Indicadores apresentados: 'self-consumption', 'self-sufficiency', Custos anuais de electricidade (€), Potência (W) e Investimento (€) no sistema de PV.",
        style={'textAlign': 'left', 'fontSize': '25px'}),
    html.Hr(),
    dbc.Row([
        # Primeira coluna: Configurações e Mapa
        dbc.Col([
            html.P("Distribuição do excedente solar", style={'textAlign': 'left', 'fontSize': '25px'}),
            html.Br(),
            dbc.Row(dcc.Dropdown(['By Demand', 'By Electricity Production'], 'By Demand', id='dropdown')),
            html.Br(),
            # Botões de execução e reset
            dbc.Row([
                dbc.Col(dbc.Button('Run Algorithm', color="primary", id='run-button'))
            ]),
            html.Br(),
            # 3d map
            dcc.Loading(
                type='graph',
                children=dash_deck.DeckGL(
                    map,
                    id="3d-map",
                    mapboxKey=mapbox_api_token,
                    tooltip=tooltip,
                    enableEvents=['click'],
                    style={"width": "45vw", "height": "60vh", "position": "relative", "zIndex": "0"}
                )
            ),
            # 2d map
            dcc.Loading(
                dcc.Loading(type='graph', children=dcc.Graph(id='2d-map'))
            ),
            dbc.Card([dbc.CardHeader(id='building-details-title', children="Building Details"),
            dbc.CardBody(
                id='building-customization-fields',
                children=[],  # Dynamically populated
            )],
            id='building-details-card',
            style={"display": "none", "position": "fixed", "top": "10%", "right": "5%", "width": "25%"}
            ),
            # Segundo gráfico (abaixo do mapa) com margem superior
            dbc.Row(
                dcc.Loading(type='graph', children=dcc.Graph(id='PV-figure')),
                style={"width": "100%", "height": "50vh"}
            )
        ], width=6),  # Define metade da largura para esta coluna
        # Segunda coluna: Configurações da Bateria e Gráficos
        dbc.Col([
            html.P("Capacidade da Bateria (1 =1x capacidade = média diária de consumo eléctrico do edifício)",
                   style={'textAlign': 'left', 'fontSize': '25px'}),
            html.Br(),
            # Input de capacidade da bateria
            dbc.Row(dcc.Input(id='battery-efficiency', type='number', value=1, min=0, max=1, step=0.1, placeholder='Eficiência da bateria')),
            html.Br(),
            # Botões de execução e reset
            dbc.Row([
                dbc.Col(dbc.Button('Reset', color="primary", id='reset-button'))
            ]),
            # Primeiro gráfico na coluna direita
            dbc.Row(
                dcc.Loading(type='graph', children=dcc.Graph(id='consumption-figure')),style={"width": "100%", "height": "50vh"}),
            html.Br(),
            # Segundo gráfico na coluna direita
            dbc.Row(dcc.Loading(type='graph', children=dcc.Graph(id='savings-figure')),style={"width": "100%", "height": "50vh"}),
            html.Br(),
        ], width=6)  # Define metade da largura para esta coluna
    ])
], fluid=True)

@callback(
    Output('3d-map', 'data'),
    Output('2d-map', 'figure'),
    Output('consumption-figure', 'figure'),
    Output('savings-figure', 'figure'),
    Output('PV-figure', 'figure'),
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

@callback(
    Output('building-details-card', 'style'),  # Control card visibility
    Output('building-details-title', 'children'),  # Title for the card
    Output('building-customization-fields', 'children'),  # Fields inside the card
    Input('2d-map', 'selectedData'),  # Detect clicks on the 2D map
    State('building-details-card', 'style'),  # Card visibility
)
def show_building_customization(selected_data, card_style):
    # If a building is clicked
    if selected_data and selected_data.get("points"):
        fields = [dbc.Row([
            dbc.Col(),
            dbc.Col(html.Label("% de área de cobertura com PV")),
            dbc.Col(html.Label("Carregamento de veículo electrico"))
        ])]
        for point in selected_data["points"]:
            building_info = point.get("customdata", {})
            print(building_info)
            building_name = next((x for x in building_info if isinstance(x, str)), None)

            # Populate the customization fields with building information
            fields.append(
                dbc.Row([
                    dbc.Col(html.Label(building_name)),
                    dbc.Col(dbc.Input(type="number", placeholder=100, min=0, max=100, step=1)),
                    dbc.Col(dbc.Select(options=[{"label": "Yes", "value": "yes"}, {"label": "No", "value": "no"}], placeholder="No"))
                ]))
        # Add save changes button to the end
        fields.append(dbc.Button("Save Changes", id="save-building-customization", color="primary"))
        # Make card visible and populate with fields
        return {"display": "block"}, "Selected Buildings", fields
    # Hide the card if no building is clicked
    return {"display": "none"}, "", []

if __name__ == '__main__':
    app.run(debug=True)
