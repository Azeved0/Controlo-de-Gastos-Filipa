import pandas as pd
import streamlit as st
from datetime import datetime
from google.oauth2.service_account import Credentials
import gspread
from streamlit_echarts import st_echarts
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# Google Sheets Setup
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1ZssUo6wfy4wZO9eQPljOTdwzF7dTSpxZ1_wNa6yGqaw"  # Replace with your Google Sheets ID

# Load credentials from Streamlit secrets
credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_CREDENTIALS"], scopes=SCOPES)

# Authenticate with Google Sheets
client = gspread.authorize(credentials)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# Read data from Google Sheets
data = sheet.get_all_values()
df = pd.DataFrame(data[1:], columns=data[0])

st.set_page_config(
    page_title="Monitorização de Gastos",
    page_icon="🪙",
    layout="wide",
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# This is a header. This is an *extremely* cool app!"
    }
)

# Set the interval to refresh every 50 minutes (3000 seconds)
st_autorefresh(interval=300 * 10000, key="keep_alive")

# Gui start
st.title("Monitorização de Gastos 😁")

with st.expander("Adicionar despesa"):
    # Add a new entry
    existing_categories = df['Category'].unique().tolist()
    category = st.selectbox("Categoria", existing_categories)
    new_category = st.text_input("Nova Categoria")
    value = st.number_input("Value", value=None)
    comments = st.text_area("Comentários")
    if new_category != "":
        category = new_category
    
    if st.button("Adicionar"):
        new_row = {
            "Insert_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Category": category,
            "Value": str(value),
            "Comments": comments
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        # Update Google Sheets
        sheet.clear()  # Clear the sheet
        sheet.update([df.columns.values.tolist()] + df.values.tolist())  # Write new data
        st.success("Despesa adicionada com sucesso!")
    
    #Tailing last records
    st.write("Últimos registos:")
    st.write(df.tail(5))
    
## Data visualization
st.header("Visualização de dados")

# Convert 'insert_date' to datetime and 'value' to float
df['Insert_date'] = pd.to_datetime(df['Insert_date'])
df['Value'] = df['Value'].astype(float)

# Creating a container to insert pretended month and respective piechart
with st.container():
    # Filter DataFrame for rows where 'insert_date' is in selected month
    month = st.selectbox("Month:",("Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"))
    month_mapping = {"Janeiro": 1,"Fevereiro": 2,"Março": 3,"Abril": 4,"Maio": 5,"Junho": 6,"Julho": 7,"Agosto": 8,"Setembro": 9,"Outubro": 10,"Novembro": 11,"Dezembro": 12}
    month_number = month_mapping[month]
    month_df = df[df['Insert_date'].dt.month == month_number]

    # Get sum of total spendings
    month_sum = sum(month_df["Value"])

    # Convert DataFrame to list of dictionaries for ECharts
    echarts_data = month_df[['Value', 'Category']].rename(columns={'Value': 'value', 'Category': 'name'}).to_dict(orient='records')

    # Group by 'Category' and sum the 'Value' column
    grouped_df = month_df.groupby('Category')['Value'].sum().round(2).reset_index()

    # Order the DataFrame by the sum of the 'Value' column in descending order
    grouped_df = grouped_df.sort_values(by='Value', ascending=False)

    # Convert DataFrame to list of dictionaries for ECharts
    echarts_data = grouped_df.rename(columns={'Value': 'value', 'Category': 'name'}).to_dict(orient='records')

    # Define the ECharts option
    option = {
        "title": {
            "text": f"Gastos por categoria",
            "subtext": f"Total de {month}: {month_sum}",
            "left": 'center'
        },
        "tooltip": {
            "trigger": 'item'
        },
        "legend": {
            "orient": 'vertical',
            "left": 'left'
        },
        "series": [
            {
                "name": 'Access From',
                "type": 'pie',
                "radius": '50%',
                "data": echarts_data,
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }
        ]
    }

    # Display the ECharts pie chart in Streamlit
    st_echarts(options=option, height="500px")

## Monthly evolution
# Extract month and year from 'Insert_date'
df['Month'] = df['Insert_date'].dt.to_period('M')

# Group by month and category, and sum the values
grouped_df = df.groupby(['Month', 'Category'])['Value'].sum().reset_index()

# Pivot the DataFrame to have months as index and categories as columns
pivot_df = grouped_df.pivot(index='Month', columns='Category', values='Value').fillna(0)

# Add a category being the sum of all other categories grouped by month
pivot_df['Total'] = pivot_df.sum(axis=1)

# Format the month display
pivot_df.index = pivot_df.index.strftime('%b %y')

# Convert the pivot table to a format suitable for ECharts
echarts_data = []
for category in pivot_df.columns:
    echarts_data.append({
        "name": category,
        "type": "line",
        "data": pivot_df[category].tolist()
    })

# Define the ECharts option
option = {
    "title": {
        "text": 'Evolução mensal'
    },
    "tooltip": {
        "trigger": 'axis'
    },
    "legend": {
        "data": pivot_df.columns.tolist(),
        "selected": {category: (category == 'Total') for category in pivot_df.columns}
    },
    "xAxis": {
        "type": 'category',
        "data": pivot_df.index.tolist()
    },
    "yAxis": {
        "type": 'value'
    },
    "series": echarts_data
}

with st.container():
    # Display the ECharts line chart in Streamlit
    st_echarts(options=option, height="500px")

## Daily evolution
# Extract day and month from Insert_date
# Extract day and month from Insert_date
df['day_num'] = df['Insert_date'].dt.day
df['month_num'] = df['Insert_date'].dt.month

# Group by Month and Day, then sum the values and accumulate over the month
daily_sum = df.groupby(['month_num', 'day_num'])['Value'].sum().reset_index()
daily_sum['Cumulative_Value'] = daily_sum.groupby('month_num')['Value'].cumsum()

# Merge the cumulative values back to the original DataFrame
df = df.merge(daily_sum[['month_num', 'day_num', 'Cumulative_Value']], on=['month_num', 'day_num'], how='left')

# Prepare data for ECharts
months = df['month_num'].unique()
series_data = []

for month in months:
    month_data = df[df['month_num'] == month]
    series_data.append({
        'name': f"{month_data['Insert_date'].iloc[0].strftime('%b %y')}",
        'type': 'line',
        'areaStyle': {},
        'data': list(zip(month_data['day_num'], month_data['Cumulative_Value']))
    })
    
# Color palette so every month stays the same color
color_palette = [
    '#ADD8E6',  # Light Blue
    '#90EE90',  # Light Green
    '#FFB6C1',  # Light Pink
    '#FFD700',  # Gold
    '#D3D3D3',  # Light Gray
    '#FFA07A',  # Light Salmon
    '#E6E6FA',  # Lavender
    '#F0E68C',  # Khaki
    '#DDA0DD',  # Plum
    '#B0E0E6',  # Powder Blue
    '#FFDEAD',  # Navajo White
    '#98FB98'   # Pale Green
]

# Extract unique days from the data
days = sorted(df['day_num'].unique())

# ECharts option
option = {
    "title": {
        "text": 'Evolução diária'
    },
    'legend': {
        'data': [series['name'] for series in series_data] 
    },
    'tooltip': {
        'trigger': 'axis',
        'formatter': '{b0}: {c0}'  # This will show the name and value
    },
    'xAxis': {
        'type': 'category',
        'boundaryGap': False,
        'data': list(range(0, 32))  # Days of the month  # Days of the month
    },
    'yAxis': {
        'type': 'value'
    },
    'series': series_data,
    'color': color_palette
}

with st.container():
    # Display the ECharts line chart in Streamlit
    st_echarts(options=option, height="500px")
