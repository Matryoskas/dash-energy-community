from dash import Dash, html, dcc, callback, Output, Input, State, ctx
import dash_bootstrap_components as dbc
from algorithm import setup, algorithm

app = Dash(__name__, external_stylesheets=[dbc.themes.MINTY])

app.layout = dbc.Container([
    dcc.Store(id='dataframes-final', data=setup()),
    html.H1(children='Custo de Energia numa Comunidade Energética', style={'textAlign': 'center'}),
    html.Hr(),
    dbc.Row([
        dbc.Col(dcc.Loading(type='graph',
                            children=dcc.Graph(id='map-figure'))),
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
    Input('map-figure', 'selectedData'),
    State('dataframes-final', 'data'),
    Input('reset-button', 'n_clicks')
)
def update_map(selectedData, data, n_clicks):
    if (ctx.triggered_id == 'reset-button'):
        print('reset')
        return algorithm(None, None)

    print('update')
    return algorithm(data, selectedData)

if __name__ == '__main__':
    app.run(debug=True)
