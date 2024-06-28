from dash import Dash, html, dcc, callback, Output, Input
import plotly.express as px
import pandas as pd
import geopandas as gpd
import dash_bootstrap_components as dbc

energy_consumption = pd.read_csv('EC_analysis_total.csv', usecols=['SS RATIO(%)', 'SC RATIO(%)'])
energy_consumption.rename(index={0: 'Without BESS', 1:'With BESS'},inplace=True)
ec_figure = px.bar(energy_consumption, barmode='group')

buildings_savings = pd.read_csv('EC_building_savings.csv', usecols=['Building', 'Ecost_base (€)', 'Ecost_SC (€)', 'Ecost_EC (€)', 'Ecost_EC_BESS (€)'])
buildings_savings.set_index('Building')
bs_figure = px.bar(buildings_savings, x='Building', y=['Ecost_base (€)', 'Ecost_SC (€)', 'Ecost_EC (€)', 'Ecost_EC_BESS (€)'], barmode='group')

buildings_shapefile = gpd.read_file('zone.shp')
gdf = buildings_shapefile.merge(buildings_savings,left_on='Name', right_on='Building',how='left')
gdf = gdf.to_crs(epsg=4326)
map_figure = px.choropleth_mapbox(gdf,
                                  geojson=gdf.geometry,
                                  locations=gdf.index,
                                  color='Ecost_base (€)',
                                  center={'lat': 38.77039, 'lon': -9.19363},
                                  mapbox_style='open-street-map',
                                  zoom=16.9,
                                  width=1000,
                                  height=1300)

app = Dash(external_stylesheets=[dbc.themes.MINTY])

app.layout = dbc.Container([
    html.H1(children='Custo de Energia numa Comunidade Energética', style={'textAlign':'center'}),
    html.Hr(),
    #dcc.Dropdown(df.country.unique(), 'Canada', id='dropdown-selection'),
    dbc.Row([
        dbc.Col(dcc.Graph(figure=map_figure)),
        dbc.Col([
            dbc.Row(dbc.Col(dcc.Graph(figure=ec_figure))),
            dbc.Row(dbc.Col(dcc.Graph(figure=bs_figure)))
        ])
    ])
], fluid=True)

#@callback(
#    Output('graph-content', 'figure'),
#    Input('dropdown-selection', 'value')
#)
#def update_graph(value):
#    dff = df[df.country==value]
#    return px.line(dff, x='year', y='pop')

if __name__ == '__main__':
    app.run(debug=True)
