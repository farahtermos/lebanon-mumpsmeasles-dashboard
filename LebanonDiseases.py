import pandas as pd
import streamlit as st
import plotly.express as px

# ---------- MAPBOX TOKEN ----------
px.set_mapbox_access_token("pk.eyJ1IjoiZmFyYWh0MTE3IiwiYSI6ImNtOWN2cDYzbTA1cGsybHNhMGd4amZrY2oifQ.UILGXLituZsWgt0k3AP6ow")

# ---------- CONSTANTS ----------
CSV_FILE_PATH = 'MumpsLeb.csv'
MAP_CENTER = {'lat': 33.95, 'lon': 35.85}
MAP_ZOOM = 8.2
MAPBOX_STYLE = 'mapbox://styles/mapbox/light-v11'

REGION_COORDS = {
    'Beqaa Valley': (33.8467, 35.9020),
    'South Governorate': (33.2721, 35.2033),
    'Beirut': (33.8938, 35.5018),
    'Mount Lebanon': (33.8333, 35.5833),
    'Tripoli': (34.4367, 35.8308),
    'Nabatieh': (33.3772, 35.4839),
    'Baalbek-Hermel': (34.1796, 36.1508),
    'Akkar': (34.5431, 36.0771)
}

# ---------- LOAD DATA ----------
@st.cache_data
def load_and_process_data(path):
    df = pd.read_csv(path)
    df['Region'] = df['refArea'].apply(lambda x: x.split('/')[-1].replace('_', ' '))
    df['Region'] = df['Region'].replace({
        'North Governorate': 'Tripoli',
        'North Lebanon': 'Tripoli'
    })
    df['Month-Year'] = pd.to_datetime(df['refPeriod'].apply(lambda x: x.split('/')[-1]), format='%m-%Y')
    df['Year'] = df['Month-Year'].dt.year
    df.rename(columns={'Number of cases': 'Cases'}, inplace=True)
    return df

# ---------- COORDINATES ----------
def add_coordinates(df):
    df['lat'] = df['Region'].map(lambda r: REGION_COORDS.get(r, (None, None))[0])
    df['lon'] = df['Region'].map(lambda r: REGION_COORDS.get(r, (None, None))[1])
    return df.dropna(subset=['lat', 'lon'])

# ---------- BUBBLE MAP ----------
def plot_bubble_map(df, year):
    df_total = df[df['Year'] == year].groupby('Region', as_index=False)['Cases'].sum()
    df_total = add_coordinates(df_total)
    df_total['Hover'] = df_total.apply(lambda row: f"{row['Region']}: {int(row['Cases'])} total cases", axis=1)

    fig = px.scatter_mapbox(
        df_total,
        lat='lat',
        lon='lon',
        size='Cases',
        size_max=40,
        zoom=MAP_ZOOM,
        center=MAP_CENTER,
        mapbox_style=MAPBOX_STYLE,
        hover_name='Hover',
        height=600
    )

    fig.update_traces(marker=dict(color='red', sizemin=5))
    fig.update_layout(showlegend=False, margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig, df_total

# ---------- STREAMLIT APP ----------
def main():
    st.set_page_config(layout="wide")
    st.title("📍 Total Mumps Cases in Lebanon")
    st.markdown("Each red circle represents a region. **Circle size = total number of mumps cases that year**.")

    df = load_and_process_data(CSV_FILE_PATH)
    years = sorted(df['Year'].unique())

    # Layout: left slider, right visuals
    left_col, right_col = st.columns([1, 3], gap="large")

    with left_col:
        st.subheader("🗓️ Select Year")
        selected_year = st.select_slider("Year", options=years, value=years[0])

    with right_col:
        map_col, text_col = st.columns([3, 1], gap="medium")

        with map_col:
            fig, df_total = plot_bubble_map(df, selected_year)
            st.plotly_chart(fig, use_container_width=True)

        with text_col:
            total_by_region = df.groupby('Region')['Cases'].sum().sort_values(ascending=False)
            top_region = total_by_region.index[0]
            total_cases = int(total_by_region.iloc[0])

            st.markdown(
                f"""
                <div style='display: flex; align-items: center; height: 100%; text-align: center;'>
                    <div style='margin: auto; font-size: 18px;'>
                        The lack of access to <strong>MMR vaccines</strong> in rural areas remains a critical challenge in Lebanon, <br>
                        with the highest number of recorded mumps cases in the <strong>{top_region}<strong>.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # ---------- LINE CHART: Mumps Trends Over Time ----------

    st.markdown("### Mumps Trends Over Time by Region")

    available_regions = sorted(df['Region'].unique())
    selected_line_regions = st.multiselect(
        "Compare regional mump cases using the dropdown:",
        options=available_regions,
        default=["Beqaa Valley"]
    )

    line_df = df[df['Region'].isin(selected_line_regions)]
    line_df = line_df.groupby(['Year', 'Region'])['Cases'].sum().reset_index()

    color_map = {region: ('indianred' if region == 'Beqaa Valley' else 'lightgrey') for region in selected_line_regions}

    line_fig = px.line(
        line_df,
        x='Year',
        y='Cases',
        color='Region',
        color_discrete_map=color_map,
        markers=True
    )

    # Clean layout: no legend, no grid lines
    line_fig.update_layout(
        showlegend=False,
        xaxis=dict(title="Year", showgrid=False, zeroline=False),
        yaxis=dict(title="Total Cases", showgrid=False, zeroline=False),
        margin=dict(l=40, r=40, t=20, b=20),
        plot_bgcolor='white'
    )

    # Label each region at the last point
    for region in selected_line_regions:
        latest_year = line_df[line_df['Region'] == region]['Year'].max()
        latest_value = line_df[(line_df['Region'] == region) & (line_df['Year'] == latest_year)]['Cases'].values[0]
        line_fig.add_annotation(
            x=latest_year,
            y=latest_value,
            text=region if region != 'Beqaa Valley' else "Beqaa",
            showarrow=False,
            font=dict(color=color_map[region], size=13),
            xanchor="left"
        )

    st.plotly_chart(line_fig, use_container_width=True)
    # ---------- BAR CHART (Sorted Descending, No Numbers) ----------
    st.markdown("### Total Mumps Cases by Region (All Years)")

    region_totals_df = df.groupby('Region')['Cases'].sum().reset_index()
    region_totals_df.columns = ['Region', 'Total Cases']
    region_totals_df = region_totals_df.sort_values(by='Total Cases', ascending=False)

    region_totals_df['Color'] = region_totals_df['Region'].apply(
        lambda x: 'indianred' if x == 'Beqaa Valley' else 'lightgrey'
    )

    bar_fig = px.bar(
        region_totals_df,
        x='Total Cases',
        y='Region',
        orientation='h',
        height=400,
        color='Color',
        color_discrete_map='identity'
    )

    bar_fig.update_layout(
        showlegend=False,
        xaxis_title="Total Cases",
        yaxis_title="",
        yaxis=dict(autorange='reversed'),
        margin=dict(l=0, r=0, t=20, b=0),
        plot_bgcolor='white'
    )

    st.plotly_chart(bar_fig, use_container_width=True)

    # ---------- FOOTER ----------
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; font-size:15px;'>"
        "For more information on the prior visualisation, please contact the creator at "
        "<a href='mailto:fat00@aubmed.ac.cy'>fat00@aubmed.ac.cy</a>. Happy Coding!"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
