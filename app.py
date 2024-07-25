from dash import Dash, html, dcc, callback, Output, Input, State, ctx
import dash_bootstrap_components as dbc
from algorithm import setup, algorithm

app = Dash(__name__, external_stylesheets=[dbc.themes.MINTY])

app.layout = dbc.Container([
    dcc.Store(id='dataframes-final', data=setup()),
    html.H1(children='Custo de Energia numa Comunidade Energética', style={'textAlign': 'center'}),
    html.Hr(),
    dbc.Row([
        dbc.Col([dbc.Row(dcc.Loading(type='graph',
                            children=dcc.Graph(id='map-figure'))),
                dbc.Row(dcc.Dropdown(['By Demand', 'By Electricity Production'], 'By Demand', id='dropdown'
                ))]),
        dbc.Col([
            dbc.Row(dcc.Loading(type='graph',
                                children=dcc.Graph(id='consumption-figure'))),
            dbc.Row(dcc.Loading(type='graph',
                                children=dcc.Graph(id='savings-figure'))),
            dbc.Row(dbc.Button('Reset', color="primary", id='reset-button'))
        ])
    ])
], fluid=True)

@callback(
    Output('map-figure', 'figure'),
    Output('consumption-figure', 'figure'),
    Output('savings-figure', 'figure'),
    Output('dropdown', 'value'),
    Input('map-figure', 'selectedData'),
    State('dataframes-final', 'data'),
    State('dropdown', 'value'),
    Input('reset-button', 'n_clicks')
)
def update_map(selectedData, data, value, n_clicks):
    if (ctx.triggered_id == 'reset-button'):
        print('reset')
        return algorithm(None, None) + ('By Demand',)

    print('update')
    return algorithm(data, selectedData, value)+ (value,)

if __name__ == '__main__':
    app.run(debug=True)
