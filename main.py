from datetime import timedelta
from datetime import datetime

import numpy as np
import streamlit as st
import pandas as pd
##import plotly.express as px
import plotly.graph_objects as go
#from Background import set_bg_hack
import smtplib
from email.message import EmailMessage

##Browser tab configuration
st.set_page_config(
    page_title="EasYdro",
    page_icon="🐚",
    layout="wide",
)

##Head Image
col1, col2, col3 = st.columns([1, 4, 1])
with col1:
    st.write(' ')
with col2:
    st.image("Chaos.PNG")
    original_title = '<p style="font-family:Courier; color:Black; font-size: 40px; text-align: center">data re-organizer.</p>'
    st.markdown(original_title, unsafe_allow_html=True)
with col3:
    st.write(' ')

st.markdown("""---""")

add_selectbox = st.sidebar.selectbox(
    "MENU",
    ("Data organiser tool", "Contact"))

if add_selectbox == "Data organiser tool":

    #st.image("File.PNG", width=25)
    data_upload = st.file_uploader('Browse your timeseries file')
    if data_upload is None:
        st.stop()

    data = pd.read_csv(data_upload)

    st.markdown("""---""")

    col1, col2 = st.columns(2)
    with col1:
        time_col = st.selectbox('What is the time column of your dataset?', (data.columns))

    data['sel_date'] = data[time_col]
    data['sel_date'] = pd.to_datetime(data['sel_date'])
    data['delta'] = (data['sel_date'] - data['sel_date'].shift()).dt.total_seconds()
    delta = np.mean(data.delta)

    if delta <= 50:
        units = ['S', 'min', 'H', 'D']
    elif delta <= 500:
        units = ['min', 'H', 'D', 'S']
    elif delta <= 43200:
        units = ['H', 'D', 'S', 'min']
    else:
        units = ['D', 'S', 'min', 'H']

    with col2:
        option = st.selectbox('What data do you want to plot?', (data.columns))
        data['sel_plot'] = data[option]

    st.markdown("""---""")

    with col1:
        TimeStep = st.number_input('Select the timestep', min_value=1, max_value=100000000000000, value=5, step=1)

    with col2:
        TimeUnit = st.selectbox('Select the time unit', units)

    data['sel_plot'] = pd.to_numeric(data['sel_plot'], errors='coerce')
    data['sel_plot'] = data['sel_plot'].astype(float)

    resamp_param = str(int(TimeStep)) + str(TimeUnit)

    star = data['sel_date'].head(1)
    end = data['sel_date'].tail(1)
    values = st.slider('Adjust your dataset time window',
                       value=[(star.dt.date[0]), (end.dt.date[len(data) - 1])])

    st.markdown("""---""")

    data = data.set_index('sel_date', drop=True)
    data = data.truncate(before=values[0], after=values[1])

    resampled_data = data.resample((resamp_param)).bfill(limit=1).interpolate()

    col3, col4, col5 = st.columns(3)
    method = ['mean', 'threshold']
    if st.checkbox("Data treatment tool"):
        with col3:
            treat_method = st.selectbox('Select the treatment type', method)
        if treat_method == 'mean':
            with col4:
                windo = st.number_input('Select the treatment window', min_value=1, max_value=100000000000000, value=5,
                                        step=1)
            resampled_data['sel_plot_av'] = resampled_data['sel_plot'].rolling(windo, min_periods=1, center=True).mean()

        if treat_method == 'threshold':
            with col4:
                thresh_min = st.number_input('Select the min threshold value', min_value=-100000000000000, max_value=100000000000000, value=int(resampled_data['sel_plot'].min()-1),
                                        step=1)
            with col5:
                thresh_max = st.number_input('Select the max threshold value', min_value=-100000000000000, max_value=100000000000000, value=int(resampled_data['sel_plot'].max()+1),
                                        step=1)

            resampled_data['sel_plot_av'] = resampled_data['sel_plot'].copy()
            for i in range(1,len(resampled_data)):
                if resampled_data['sel_plot'][i] <= thresh_min:
                    resampled_data['sel_plot_av'][i] = resampled_data['sel_plot_av'][i-1]
                elif resampled_data['sel_plot'][i] >= thresh_max:
                    resampled_data['sel_plot_av'][i] = resampled_data['sel_plot_av'][i-1]
                else:
                    resampled_data['sel_plot_av'][i] = resampled_data['sel_plot'][i]

    #st.dataframe(resampled_data)

    # PLOT
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data['sel_plot'],
                             mode='lines',
                             name='Raw data'))

    fig.add_trace(go.Scatter(x=resampled_data.index, y=resampled_data['sel_plot'],
                             mode='lines',
                             name='Resampled data'))

    try:
        fig.add_trace(go.Scatter(x=resampled_data.index, y=resampled_data['sel_plot_av'],
                                 mode='lines',
                                 name='Treated resampled data'))
        # st.write(fig)
    except KeyError:
        pass

    fig.update_layout(
        # title="Plot Title",
        xaxis_title=time_col,
        yaxis_title=option)
    # legend_title="Legend Title",

    st.write(fig)

    ###Download button
    try:
        final_df = pd.DataFrame({'time': resampled_data.index,
                                 str(option): resampled_data.sel_plot,
                                 str(option) + '_treated': resampled_data['sel_plot_av']})
    except KeyError:
        final_df = pd.DataFrame({'time': resampled_data.index,
                                 str(option): resampled_data.sel_plot})

    csv = final_df.to_csv(index=False).encode('utf-8')

    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name='treated data.csv',
        mime='text/csv',
    )

    with st.expander('Input simulator formatting'):
        model_name = ['SWMM', 'InfoWorks', 'WEST']
        simulator = st.selectbox('Select the simulator', model_name)
        resampled_data = resampled_data.reset_index('sel_date')
        if simulator == 'SWMM':
            formatted_data = []
            RG_name = st.text_input('Enter a raingauge name')
            resampled_data['SWMM_date'] = resampled_data.sel_date.dt.strftime('%m  %d  %Y %H  %M')
            try:
                formatted_data = pd.DataFrame({'RG': RG_name,
                                               'date': resampled_data['SWMM_date'],
                                               'Treated resampled value': resampled_data['sel_plot_av']})
            except KeyError:
                formatted_data = pd.DataFrame({'RG': RG_name,
                                               'date': resampled_data['SWMM_date'],
                                               'Resampled value': resampled_data['sel_plot']})
            st.write(formatted_data)

        elif simulator == 'WEST':
            formatted_data = []
            RG_name = st.text_input('Enter a raingauge name')
            resampled_data = resampled_data.reset_index()
            resampled_data['WEST_date'] = (resampled_data.sel_date - resampled_data.sel_date.shift()).dt.total_seconds()
            resampled_data['WEST_date'] = np.cumsum(resampled_data['WEST_date'] / 60 / 60 / 24)
            resampled_data['WEST_date'][0] = 0.0
            valUnit = st.text_input('write the units')
            try:
                formatted_data = pd.DataFrame({'#.t \n #d': resampled_data['WEST_date'],
                                               str(RG_name): resampled_data['sel_plot_av']})
            except KeyError:
                formatted_data = pd.DataFrame({'#.t\n'
                                               '#d': resampled_data['WEST_date'],
                                               str(RG_name): resampled_data['sel_plot']})
            formatted_data.loc[0] = [50, 0.0]
            formatted_data.columns = pd.MultiIndex.from_arrays(formatted_data.iloc[0:1].values)
            st.write(formatted_data)

if add_selectbox == "Contact":
    st.write('This is an experimental App.')
    st.write('Please feel free to share how much you like or not the app, '
             'what does not work or what you would like to have. I do not guarantee to have it, but can try to do something!')
    with st.form("my_form"):
        fullname = st.text_input('Fullname')
        email = st.text_input('Email')
        message = st.text_area('Message', value='Hello, your app is amazing but...')#
        submitted = st.form_submit_button("Submit")

        if submitted:
            msg = EmailMessage()
            msg.set_content(message)
            email_address = 'easydro07@gmail.com'
            msg['Subject'] = 'From  ' + email
            msg['From'] = email_address
            msg['To'] = email_address
            passcode = 'jeetaqchprvyqdbu'        # add passcode here

            conn = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            conn.login(email_address, passcode)
            conn.send_message(msg)
            conn.quit()
            st.success('Thank you for your message !')