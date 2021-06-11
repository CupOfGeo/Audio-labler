import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash.exceptions import PreventUpdate
import dash_table
import pandas as pd
import base64
import io
from pydub import AudioSegment

#maybe i should write docs for this bc i dont wanna work on functionality right now

# this is just the columns of the dataframe the user is making
# its currently a global but will be move to a local store in deployment
df = pd.DataFrame(columns=['character', 'time_start', 'time_end', 'tone', 'transcript'])

app = dash.Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])

# the list of characters for dropdown menu hard coded make as input for generalization of other shows
characters = ['Rick', 'Morty', 'Jerry', 'Summer', 'Beth']
char_options = [{'label': x, 'value': x} for x in characters]

# temp test audio and subtitles file to use for functionality testing
clip = AudioSegment.from_mp3('/assets/rick_temp/S01E03 - Anatomy Park.mp3')

subtitles_file = open('/assets/rick_temp/Rick.and.Morty.S01E03.720p.BluRay.x264.DAA.srt')


app.layout = dbc.Container(
    [
        # dcc.Store(id='mp3_session', storage_type='session'),
        # maybe use this to store the dataframes instead

        # upload mp3 and subtitle srt files
        # the mp3 is going to need to be sent to a bucket with a life cycle
        dcc.Upload(
            id='upload-mp3',
            children=html.Div([
                html.A('Select Episode mp3 file')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            # Allow multiple files to be uploaded
            multiple=True
        ),

        dcc.Upload(
            id='upload-data',
            children=html.Div([
                html.A('Select Subtitles SRT file')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            # Allow multiple files to be uploaded
            multiple=True
        ),

        # i don't know why i made this
        # i think it can be use to hold the index of the audio clip or something
        # html.Div(id='output-data-upload'),

        html.H3("Audio Labeler",
                style={'text-align': 'center'}),
        # audio out trying to add pause feature that will update the time clip
        # look into n_click_timestamp https://dash.plotly.com/dash-html-components/audio
        dbc.Row(
            html.Audio(id='audio_out',src='rick_voice.wav', controls=True, style={'display': 'block', 'margin': '0 auto'})
        ),

        #how much to offset the time gotten from the subtitle file
        dbc.Row(
            [
                dbc.Col(dbc.Input(id='start_offset', value=0, placeholder='start time offset', type="number",debounce=True)),
                dbc.Col(dbc.Input(id='end_offset', value=0, placeholder='end time offset', type="number",debounce=True))
            ]
        ),
        #the transcription of the audio file
        dbc.Row(
            [
                dbc.Col(dbc.Input(id='transcript', placeholder='transcription'))
            ]
        ),
        #character dropdown and tone notes
        dbc.Row(
            [
                dbc.Col(dcc.Dropdown(id='char-dd', options=char_options, value=characters[0])),
                dbc.Col(dbc.Input(id='tone', placeholder='tone/notes')),
            ]
        ),
        #save the clip to the out_df or skip that time stamp
        dbc.Row(
            [
                #dbc.Col(dbc.Button('Prev', id='prev')),
                dbc.Col(dbc.Button('Save & Next', id='save')),
                dbc.Col(dbc.Button('Skip', id='skip')),
            ]
        ),
        # where the out_df should be displayed
        html.Div(id='table_div', children=[

            # dash_table.DataTable(id='table', columns=[{"name": i, "id": i} for i in df.columns],
            #                      data=df.to_dict('records'),
            #                      )
        ])

    ], className="p-5"
)


def to_sub(file):
    r = file.read()
    read_file = r.split('\n')

    sub_line = []
    groups = []
    # print(len(read_file))
    # taking one group of data and putting it all on one line
    for line in read_file:
        if line != '\r':
            sub_line.append(line)
        else:
            if sub_line != []:
                groups.append(sub_line)
            sub_line = []

    line = []
    timestart = []
    timeend = []

    for group in groups:
        line.append((" ".join(group[2:])))

        # turn time into seconds
        unformat_time = group[1]
        left, right = unformat_time.split('-->')
        left = left.replace(' ', '').split(':')
        right = right.replace(' ', '').split(':')
        left_sum = int(left[0]) * 60 * 60 * 1000 + int(left[1]) * 60 * 1000 + int(left[2].replace(',', '')) + 500
        right_sum = int(right[0]) * 60 * 60 * 1000 + int(right[1]) * 60 * 1000 + int(right[2].replace(',', '')) + 500
        timestart.append(left_sum)
        timeend.append(right_sum)
        # print(left_sum, right_sum)
        # print(left,right)

    sub_df = pd.DataFrame({'TimeStart': timestart, 'TimeEnd': timeend, 'Text': line})

    return sub_df


def parse_contents(contents, filename, date):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    # print(io.BytesIO(decoded.decode('utf-8')))
    # print(decoded)

    try:
        with io.BytesIO(decoded) as buffer:
            sb = io.TextIOWrapper(buffer, 'utf-8', newline='')
            # print(sb.read())
            sub_df = to_sub(sb)

    except Exception as e:
        print(e)
        return pd.DataFrame()
        # return html.Div([
        #     'There was an error processing this file.'
        # ])
    return sub_df


# todo re-wirte as it shouldn't be at the bottom just a test to make sure im parsing the data correctly
# the data should be in a stored obj
@app.callback(Output('table_div', 'children'),
              Input('upload-data', 'contents'),
              State('upload-data', 'filename'),
              State('upload-data', 'last_modified'))
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [parse_contents(c, n, d) for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)]

        out_table = dash_table.DataTable(id='table', columns=[{"name": i, "id": i} for i in children[0].columns],
                                         data=children[0].to_dict('records'))

        return out_table


# decodes the mp3 to byte code and saves it to a file now i can open the file as a buffer
# and open it with the audio segmentation thing
def parse_mp3_upload(contents):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    with io.BytesIO(decoded) as buffer:
        clip = AudioSegment.from_mp3(buffer)
        # clip[10000:30000].export("10secs.mp3", format="mp3")
        # this works now how do i get it from here to the screen without saving it





# store the uploaded mp3 to store local object
# the test can be if i can hear it in the audio button
@app.callback(Output('mp3_session', 'data'),
              Input('upload-mp3', 'contents'),
              State('upload-mp3', 'filename'),
              State('upload-mp3', 'last_modified'),
              State('mp3_session', 'data'))
def update_output(list_of_contents, list_of_names, list_of_dates, data):
    # print('Hello?')
    if list_of_contents is not None:
        print(list_of_names)
        #parse_mp3_upload(list_of_contents[0])
        # Give a default data dict with 0 clicks if there's no data.
        data = data or {'mp3': 0}
        data['mp3'] = list_of_contents[0]
        return data
    else:
        raise PreventUpdate


@app.callback(Output('audio_out', 'src'),
              Input('end_offset', 'value'),
              Input('start_offset', 'value'))
def stop_me(drop):
    # wack kill me Reiners talking to me again

    return clip[start:end]



# collapse functionality to drop down the the data table
# collapse = html.Div(
#     [
#         dbc.Button(
#             "Open collapse",
#             id="collapse-button",
#             className="mb-3",
#             color="primary",
#         ),
#         dbc.Collapse(
#             dbc.Card(dbc.CardBody("This content is hidden in the collapse")),
#             id="collapse",
#         ),
#     ]
# )
#
#
# @app.callback(
#     Output("collapse", "is_open"),
#     [Input("collapse-button", "n_clicks")],
#     [State("collapse", "is_open")],
# )
# def toggle_collapse(n, is_open):
#     if n:
#         return not is_open
#     return is_open


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')
