import os
import pathlib
import re
import requests, base64
import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
from dash.dependencies import Input, Output, State
from datetime import date
from datetime import timedelta
import cufflinks as cf
import numpy as np
import json

# Initialize

app = dash.Dash(
    __name__,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ]
)

server = app.server

# MAPBOX TOKEN
mapbox_access_token = 'pk.eyJ1IjoicGVkcm9lc2NvYmVkb2IiLCJhIjoiY2tibG4yeTMyMDlxNzJzbjhtNWRxdnR4MSJ9.Oldsna3sT8yMl8u8QK7xaQ'
mapbox_style = 'mapbox://styles/pedroescobedob/ckblnkcbo0lv81ipamqba19yr'

# Load data
APP_PATH = str(pathlib.Path(__file__).parent.resolve())

df_lat_lon = pd.read_csv(
    os.path.join(APP_PATH, os.path.join("data", "lat_lon_counties.csv"))
)

df_lat_lon['FIPS '] = df_lat_lon['FIPS '].apply(lambda x: str(x).zfill(5))

# HEART DISEASE DATA
df_heart_disease = pd.read_csv(
    os.path.join(
        APP_PATH, os.path.join("data", "df_with_lan_lon.csv")
    )
)
df_heart_disease['County Code'] = df_heart_disease['County Code'].apply(lambda x: str(x).zfill(5))

# COVID-19 DATA
today = (date.today() - timedelta(days=2)).strftime("%m-%d-%Y")
covid_url = f'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports/07-10-2020.csv'

covid_df = pd.read_csv(covid_url)
print(covid_df)
covid_df['FIPS'] = covid_df['FIPS'].apply(lambda x: str(x).zfill(5))

# RENAME COLUMN
df_heart_disease = df_heart_disease.rename(columns={'Heart Disease Value': 'Confirmed_cases'})
covid_df = covid_df.rename(columns={'Admin2': 'County', 'Confirmed': 'Confirmed_cases'})

# MODIFICATIONS NEEDED FOR THE COVID DATA
covid_df['County'] = (covid_df['County'].map(str) + ', ' + covid_df.County.map(str))

def remove_last2_num(num):   # Function to remove to innecessary values
    return num.strip('"')[:-2]

covid_df['Year'] = 2021
covid_df['Year'] = covid_df['Year'].astype(int)
covid_df['County Code'] = covid_df['FIPS'].apply(remove_last2_num)
covid_df['County Code'] = covid_df['County Code'].replace({'00n': '0'})
covid_df['County Code'] = covid_df['County Code'].apply(lambda x: str(x).zfill(5))

# SET YEAR
YEARS = [2018, 2020, 2021]

# BINS
HEART_BINS = [
    "0-94",
    "94.1-100",
    "100.1-120",
    "120.1-140",
    "141.1-160",
    "160.1-180",
    "181.1-200",
    "200.1-220",
    "220.1-240",
    "240.1-260",
    "260.1-280",
    "280.1-290",
    "290.1-300",
    "300.1-310",
    "310.1-330",
    ">330.1",
]

# COVID BINS
COVID_BINS = [
    "0-100",
    "101-150",
    "151-300",
    "301-500",
    "501-1000",
    "1001-1500",
    "1501-2000",
    "2001-2500",
    "2501-5000",
    "5001-7500",
    "7501-10000",
    "10001-20000",
    "20001-30000",
    "30001-40000",
    "40001-50000",
    ">50001",
]

# COLOR BIN SCALES
DEFAULT_COLORSCALE = [
    "#f2fffb",
    "#bbffeb",
    "#98ffe0",
    "#79ffd6",
    "#6df0c8",
    "#69e7c0",
    "#59dab2",
    "#45d0a5",
    "#31c194",
    "#2bb489",
    "#25a27b",
    "#1e906d",
    "#188463",
    "#157658",
    "#11684d",
    "#10523e",
]

RED_COLORSCALE = [ #COVID
    "#ffcccc",
    "#ffb2b2",
    "#ff9999",
    "#ff7f7f",
    "#ff6666",
    "#ff4c4c",
    "#ff3232",
    "#ff1919",
    "#ff0000",
    "#ff0000",
    "#e50000",
    "#cc0000",
    "#b20000",
    "#990000",
    "#7f0000",
    "#660000",
]

# APP LAYOUT ------------------------

app.layout = html.Div(
    id='root',
    children=[
        html.Div(
            id='header',
            children=[
                html.H4(children='Health problems'),
                html.P(
                    id='description',
                    children='Health problems listed by year'
                )
            ]
        ),
        html.Div(
            id='app-container',
            children=[
                html.Div(
                    id='left-column',
                    children=[
                        html.Div(
                            id='slider-container',
                            children=[
                                html.P(
                                    id='slider-text',
                                    children='Drag the slider to change the year'
                                ),
                                dcc.Slider(
                                    id='years-slider',
                                    min=min(YEARS),
                                    max=max(YEARS),
                                    value=max(YEARS),
                                    marks={
                                        str(year): {
                                            'label': str(year),
                                            'style': {'color': '#7fafdf'},
                                        }
                                        for year in YEARS
                                    },
                                )
                            ]
                        ),
                        html.Div(
                            id='heatmap-container',
                            children=[
                                html.P(
                                    'Heat-map of adjusted mortality rates {0}'.format(min(YEARS)),
                                    id='heatmap-title',
                                ),
                                dcc.Graph(
                                    id='county-choropleth',
                                    figure=dict(
                                        layout=dict(
                                            mapbox=dict(
                                                accesstoken=mapbox_access_token,
                                                style=mapbox_style,
                                                center=dict(
                                                    lat=38.72490, lon=-95.61446
                                                ),
                                                pitch=0,
                                                zoom=3.5,
                                            ),
                                            autosize=True,
                                        ),
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    id='graph-container',
                    children=[
                        html.P(
                            id='chart-selector',
                            children='Select chart:'
                        ),
                        dcc.Dropdown(
                            options=[
                                {
                                    'label': 'Heart Disease',
                                    'value': 'Heart Disease',
                                 },
                                {
                                    'label': 'COVID-19',
                                    'value': 'COVID-19',
                                }
                            ],
                            value='Heart Disease',
                            id='chart-dropdown',
                        ),
                        dcc.Graph(
                            id='selected-data',
                            figure=dict(
                                data=[
                                    dict(x=0, y=0)
                                ],
                                layout=dict(
                                    paper_bgcolor = '#F4F4F8',
                                    plot_bgcolor='#F4F4F8',
                                    autofill=True,
                                    margin=dict(t=75, r=50, b=100, l=50)
                                )
                            )
                        )
                    ]
                )
            ]
        )
    ]
)

# DEFINE APP CALLBACKS FOR THE DATA SELECTION

# YEAR SELECTION CALLBACK

@app.callback(
    Output("county-choropleth", 'figure'),
    [Input("years-slider", 'value')],
    [State("county-choropleth", 'figure')],
)

def display_map(year, figure):
    cm = dict(zip(HEART_BINS, DEFAULT_COLORSCALE))
    cm_covid = dict(zip(COVID_BINS, RED_COLORSCALE))
    # SET UP FOR THE BIN COLORS

    # latitudes and longitudes
    data = [
        dict(
            lat=df_lat_lon['Latitude'],
            lon=df_lat_lon['Longitude'],
            text=df_lat_lon['Hover'],
            type='scattermapbox',
            hoverinfo='text',
            marker=dict(size=5, color='white', opacity=0)
        )
    ]

    # DISPLAY BIN VALUES ON MAP
    if year == 2018:
        annotations = [
            dict(
                showarror=False,
                align='right',
                text='<b>HEART DISEASE VALUES PER 100,000',
                font=dict(color='#2cfec1'),
                bgcolor='#1f2630',
                x=0.85,
                y=0.85,
            )
        ]

    #COVID
    if year == 2021:
        annotations = [
            dict(
                showarror=False,
                align='right',
                text='<b>COVID-19 CASES',
                font=dict(color='#2cfec1'),
                bgcolor='#1f2630',
                x=0.90,
                y=0.85,
            )
        ]

    if year == 2018:
        for i, bin in enumerate((HEART_BINS)):
            color = cm[bin]
            annotations.append(
                dict(
                    arrowcolor=color,
                    text=bin,
                    x=0.95,
                    y=0.85 - (i/20),
                    ax=-60,
                    ay=0,
                    arrowwidth=5,
                    arrowhead=0,
                    bgcolor='#1f2630',
                    font=dict(color='#2cfec1'),
                )
            )
    #COVID
    if year == 2021:
        for i, bin in enumerate((COVID_BINS)):
            color = cm_covid[bin]
            annotations.append(
                dict(
                    arrowcolor=color,
                    text=bin,
                    x=0.95,
                    y=0.85 - (i/20),
                    ax=-60,
                    ay=0,
                    arrowwidth=5,
                    arrowhead=0,
                    bgcolor='#1f2630',
                    font=dict(color='#2cfec1'),
                )
            )


    # WHERE MAP WILL BE DISPLAYED
    if 'layout' in figure:
        lat = figure['layout']['mapbox']['center']['lat']
        lon = figure['layout']['mapbox']['center']['lon']
        zoom = figure['layout']['mapbox']['zoom']
    else:
        lat = 38.72490
        lon = -95.61446
        zoom = 3.5

    layout = dict(
        mapbox=dict(
            layers=[],
            accesstoken=mapbox_access_token,
            style=mapbox_style,
            center=dict(lat=lat, lon=lon),
            zoom=zoom,
        ),
        hovermoved='closest',
        margin=dict(r=0, l=0, t=0, b=0),
        annotations=annotations,
        dragmode='lasso',
    )

    # AQUIRE GEOMETRIC SHAPES FOR THE MAP
    if year == 2018:
        base_url = 'https://raw.githubusercontent.com/pedroescobedob/mapboxCountiesGeoJson/master/'
        for bin in HEART_BINS:
            geo_layer = dict(
                sourcetype='geojson',
                source=base_url + str(year) + '/' + bin + '.geojson',
                type='fill',
                color=cm[bin],
                opacity=0.8,
                fill=dict(outlinecolor='#afafaf'),
            )
            layout['mapbox']['layers'].append(geo_layer)

    if year == 2021:
        base_url = 'https://raw.githubusercontent.com/pedroescobedob/mapboxCountiesGeoJson/master/'
        for bin in COVID_BINS:
            geo_layer = dict(
                sourcetype='geojson',
                source=base_url + str(year) + '/' + bin + '.geojson',
                type='fill',
                color=cm_covid[bin],
                opacity=0.8,
                fill=dict(outlinecolor='#afafaf'),
            )
            layout['mapbox']['layers'].append(geo_layer)

    fig = dict(data=data, layout=layout)
    return fig

# DISPLAY SELECTED DATA

@app.callback(
    Output('selected-data', 'figure'),
    [
        Input('county-choropleth', 'selectedData'),
        Input('chart-dropdown', 'value'),
        Input('years-slider', 'value')
    ]
)

def display_selected_data(selectedData, chart_dropdown, year):
    if selectedData is None:
        return dict(
            data=[dict(x=df_heart_disease['County'], y=df_heart_disease['Confirmed_cases'])],
            layout=dict(
                title='Click-drag on the map to select counties',
                paper_bgcolor='#1f2630',
                plot_bgcolor='#1f2630',
                font=dict(color='#2cfec1'),
                margin=dict(t=75, r=50, b=100, l=75),
            ),
        )

    # SELECTED DATA
    pts = selectedData['points']
    fips = [str(pt['text'].split('<br>')[-1]) for pt in pts]
    for i in range(len(fips)):
        if len(fips[i]) == 4:
            fips[i] = '0' + fips[i]

    df1 = df_heart_disease[df_heart_disease['County Code'].isin(fips)]
    df1 = df1.sort_values('Year')

    df2 = covid_df[covid_df['County Code'].isin(fips)]
    df2 = df2.sort_values('Year')

    # BAR CHART
    if 'Heart Disease' == chart_dropdown:
        df1 = df1[df1.Year == year]
        title = 'Heart Disease'
        aggregate_by = 'Confirmed_cases'

        df1[aggregate_by] = pd.to_numeric(df1[aggregate_by], errors='coerce')
        heart_disease_values = df1.groupby('County')[aggregate_by].sum()
        heart_disease_values = heart_disease_values.sort_values()

        # only look at non zero values
        heart_disease_values = heart_disease_values[heart_disease_values > 0]

        # PLOT IN BARCHART
        if 'Heart Disease' == chart_dropdown:
            fig = heart_disease_values.iplot(
                kind='bar', y=aggregate_by, title=title, asFigure=True
            )

            fig['data'] = fig['data'][0:500]
            fig_data = fig['data']
            fig_layout = fig['layout']

            fig_data[0]['text'] = heart_disease_values.values.tolist()
            fig_data[0]['marker']['color'] = '#2cfec1'
            fig_data[0]['marker']['opacity'] = 1
            fig_data[0]['marker']['line']['width'] = 0
            fig_layout['yaxis']['title'] = 'Values for 100,000'
            fig_layout['xaxis']['title'] = 'County'
            fig_layout['yaxis']['fixedrange'] = True
            fig_layout['xaxis']['fixedrange'] = True
            fig_layout['hovermode'] = 'closest'
            fig_layout['title'] = '<b>{0}</b> counties selected'.format(len(fips))
            fig_layout['legend'] = dict(orientation='v')
            fig_layout['autosize'] = True
            fig_layout['paper_bgcolor'] = '#1f2630'
            fig_layout['plot_bgcolor'] = '#1f2630'
            fig_layout['font']['color'] = '#2cfec1'
            fig_layout['yaxis']['tickfont']['color'] = '#2cfec1'
            fig_layout['xaxis']['tickfont']['color'] = '#2cfec1'
            fig_layout['xaxis']['gridcolor'] = '#5b5b5b'
            fig_layout['yaxis']['gridcolor'] = '#5b5b5b'

            if len(fips) > 100:
                fig['layout']['title'] = 'Heart Disease Value'
            return fig

        if 'Heart Disease' == chart_dropdown:
            fig = df1.iplot(
                kind='area',
                x='Year',
                y='Confirmed_cases',
                text='County',
                categories='County',
                colors=[
                    '#FF0000',
                    '#FF0000',
                    '#7570b3',
                    '#e7298a',
                    '#66a61e',
                    '#e6ab02',
                    '#e6ab02',
                    '#666666',
                    '#1b9e77',
                ],
                vline=[year],
                asFigure=True
            )

    #covid
    elif 'COVID-19' == chart_dropdown:
        df2 = df2[df2.Year == year]
        title = 'COVID-19'
        aggregate_by = 'Confirmed_cases'

        df2[aggregate_by] = pd.to_numeric(df2[aggregate_by], errors='coerce')
        covid_value = df2.groupby('County')[aggregate_by].sum()
        covid_value = covid_value.sort_values()

        # only look at non zero values
        covid_value = covid_value[covid_value > 0]

        # PLOT IN BARCHART
        if 'COVID-19' == chart_dropdown:
            fig = covid_value.iplot(
                kind='bar', y=aggregate_by, title=title, asFigure=True
            )

        fig_data = fig['data']
        fig_layout = fig['layout']

        fig_data[0]["text"] = covid_value.values.tolist()
        fig_data[0]["marker"]["color"] = "#ff0000"
        fig_data[0]["marker"]["opacity"] = 1
        fig_data[0]["marker"]["line"]["width"] = 0
        fig_data[0]["textposition"] = "outside"
        fig_layout["paper_bgcolor"] = "#1f2630"
        fig_layout["plot_bgcolor"] = "#1f2630"
        fig_layout["font"]["color"] = "#ff0000"
        fig_layout["title"]["font"]["color"] = "#ff0000"
        fig_layout["xaxis"]["tickfont"]["color"] = "#ff0000"
        fig_layout["yaxis"]["tickfont"]["color"] = "#ff0000"
        fig_layout["xaxis"]["gridcolor"] = "#5b5b5b"
        fig_layout["yaxis"]["gridcolor"] = "#5b5b5b"
        fig_layout["margin"]["t"] = 75
        fig_layout["margin"]["r"] = 50
        fig_layout["margin"]["b"] = 100
        fig_layout["margin"]["l"] = 50

        return fig

        if 'COVID-19' == chart_dropdown:
            fig = df2.iplot(
                kind='area',
                x='Year',
                y='Confirmed_cases',
                text='County',
                categories='County',
                colors=[
                    "#FF0000",
                    "#FF0000",
                    "#7570b3",
                    "#e7298a",
                    "#66a61e",
                    "#e6ab02",
                    "#a6761d",
                    "#666666",
                    "#1b9e77",
                ],
                vline=[year],
                asFigure=True
            )

    for i, trace in enumerate(fig['data']):
        trace['mode'] = 'lines+makers'
        trace['marker']['size'] = 4
        trace['marker']['line']['width'] = 1
        trace['type'] = 'scatter'
        for prop in trace:
            fig['data'][i][prop] = trace[prop]


if __name__ == '__main__':
    app.run_server(debug=True)
