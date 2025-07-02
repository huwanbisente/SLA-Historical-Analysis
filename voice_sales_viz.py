import streamlit as st
import pandas as pd
import plotly.express as px
import os

def run_voice_sales_dashboard():

    # --- CONFIG ---
    DATA_DIR_CURRENT = "Filtered/Voice_Sales_SLA"
    DATA_DIR_BEFORE = "Filtered_before/SLA_PBI_VOICE HOURLY Inbound Sales"

    # --- Helper: Convert HH:MM:SS or MM:SS to seconds
    def to_seconds(time_str):
        try:
            return pd.to_timedelta("00:" + time_str if len(time_str.split(":")) == 2 else time_str).total_seconds()
        except:
            return 0

    # --- Load All CSVs from Folder
    @st.cache_data
    def load_all_csvs(path):
        all_files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".csv")]
        df_list = [pd.read_csv(file) for file in all_files]
        return pd.concat(df_list, ignore_index=True)

    # --- Label dataset origin
    @st.cache_data
    def load_with_period_tag():
        df_now = load_all_csvs(DATA_DIR_CURRENT)
        df_now['PERIOD'] = 'Current'
        df_before = load_all_csvs(DATA_DIR_BEFORE)
        df_before['PERIOD'] = 'Before'
        return pd.concat([df_now, df_before], ignore_index=True)

    # --- Start of App ---
    st.title("📞 SLA Voice Sales Hourly Dashboard")

    try:
        df = load_with_period_tag()

        # --- Parse date and time fields ---
        df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce', dayfirst=True)
        df = df.dropna(subset=['DATE'])  # Drop rows with invalid dates

        # Convert time strings to seconds
        df['QUEUE_TIME (s)'] = df['Average QUEUE WAIT TIME'].astype(str).apply(to_seconds)
        df['HANDLE_TIME (s)'] = df['Average HANDLE TIME'].astype(str).apply(to_seconds)
        df['ACW_TIME (s)'] = df['Average AFTER CALL WORK TIME'].astype(str).apply(to_seconds)

        # Clean and convert service level to float
        df['SERVICE LEVEL (%rec)'] = (
            df['SERVICE LEVEL (%rec)']
            .astype(str)
            .str.replace('%', '', regex=False)
            .str.strip()
            .replace('', '0')
            .astype(float)
        )

        df['ABANDONED count'] = pd.to_numeric(df['ABANDONED count'], errors='coerce').fillna(0).astype(int)
        df['CALLS'] = pd.to_numeric(df['CALLS'], errors='coerce').fillna(0).astype(int)

        df['WEEKDAY'] = df['DATE'].dt.day_name()

        def get_peak_label(hour_str):
            hour = int(str(hour_str).split(":")[0])
            return 'Peak' if 9 <= hour <= 18 else 'Off-Peak'

        df['PEAK_LABEL'] = df['HOUR'].apply(get_peak_label)

        # --- Sidebar Filters ---
        st.sidebar.header("🔎 Filters")
        if st.sidebar.button("🔄 Reset All Filters"):
            st.experimental_rerun()

        selected_periods = st.sidebar.multiselect("Dataset Period", ['Current', 'Before'], default=['Current', 'Before'])
        df = df[df['PERIOD'].isin(selected_periods)]

        skill_filter = st.sidebar.multiselect("Skill", df['SKILL'].unique(), default=df['SKILL'].unique())

        min_date = df['DATE'].min()
        max_date = df['DATE'].max()
        date_range = st.sidebar.date_input("Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

        hour_options = sorted(df['HOUR'].unique(), key=lambda x: int(str(x).split(":")[0]))
        hour_filter = st.sidebar.multiselect("Hour(s)", hour_options, default=hour_options)

        weekday_filter = st.sidebar.multiselect("Weekday(s)", list(df['WEEKDAY'].unique()), default=list(df['WEEKDAY'].unique()))
        peak_filter = st.sidebar.multiselect("Time Type", ['Peak', 'Off-Peak'], default=['Peak', 'Off-Peak'])

        df_filtered = df[
            df['SKILL'].isin(skill_filter) &
            df['HOUR'].isin(hour_filter) &
            df['WEEKDAY'].isin(weekday_filter) &
            df['PEAK_LABEL'].isin(peak_filter) &
            df['DATE'].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]))
        ]

        # --- Daily Aggregation ---
        daily = df_filtered.groupby(['DATE', 'PERIOD']).agg(
            TOTAL_CALLS=('CALLS', 'sum'),
            ABANDONED=('ABANDONED count', 'sum'),
            AVG_QUEUE=('QUEUE_TIME (s)', 'mean'),
            AVG_HANDLE=('HANDLE_TIME (s)', 'mean'),
            AVG_ACW=('ACW_TIME (s)', 'mean'),
            AVG_SLVL=('SERVICE LEVEL (%rec)', 'mean')
        ).reset_index()

        daily['% ABANDONED'] = (daily['ABANDONED'] / daily['TOTAL_CALLS']) * 100

        # --- Summary Metrics ---
        st.markdown("### 📌 Summary Metrics by Period")
        summary = df_filtered.groupby('PERIOD').agg(
            TOTAL_CALLS=('CALLS', 'sum'),
            TOTAL_ABANDONED=('ABANDONED count', 'sum'),
            AVG_QUEUE=('QUEUE_TIME (s)', 'mean'),
            AVG_HANDLE=('HANDLE_TIME (s)', 'mean'),
            AVG_ACW=('ACW_TIME (s)', 'mean'),
            MAX_Q=('QUEUE_TIME (s)', 'max'),
            MIN_Q=('QUEUE_TIME (s)', 'min'),
            AVG_SLVL=('SERVICE LEVEL (%rec)', 'mean')
        ).reset_index()
        summary['% ABANDONED'] = (summary['TOTAL_ABANDONED'] / summary['TOTAL_CALLS']) * 100

        for _, row in summary.iterrows():
            st.markdown(f"#### 📅 {row['PERIOD']} Period")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📞 Total Calls", f"{int(row['TOTAL_CALLS']):,}")
                st.metric("❌ Abandoned", f"{int(row['TOTAL_ABANDONED']):,}")
                st.metric("🎯 SL %", f"{row['AVG_SLVL']:.1f}%")
            with col2:
                st.metric("⏳ Avg Queue", f"{row['AVG_QUEUE'] / 60:.2f} mins")
                st.metric("📞 Avg Handle", f"{row['AVG_HANDLE'] / 60:.2f} mins")
                st.metric("🧾 Avg ACW", f"{row['AVG_ACW'] / 60:.2f} mins")
            with col3:
                st.metric("📉 % Abandoned", f"{row['% ABANDONED']:.1f}%")
                st.metric("⏱️ Max Queue", f"{row['MAX_Q'] / 60:.2f} mins")
                st.metric("⏱️ Min Queue", f"{row['MIN_Q'] / 60:.2f} mins")

        # --- Abandonment Trend
        st.markdown("### ❌ Abandonment % Trend")
        fig_abd = px.line(
            daily, x='DATE', y='% ABANDONED', color='PERIOD',
            markers=True, title="Abandonment Rate Over Time", width=1000
        )
        st.plotly_chart(fig_abd, use_container_width=False)

        # --- Average ACW Trend
        st.markdown("### 🧾 Average ACW Trend")
        fig_acw = px.line(
            daily, x='DATE', y='AVG_ACW', color='PERIOD',
            title="ACW Trend Over Time", markers=True,
            labels={'AVG_ACW': 'ACW (s)'}, width=1000
        )
        st.plotly_chart(fig_acw, use_container_width=False)

        # --- Service Level Trend
        st.markdown("### 🎯 Service Level Trend")
        fig_slvl = px.line(
            daily, x='DATE', y='AVG_SLVL', color='PERIOD',
            title="Service Level (%) Over Time", markers=True, width=1000
        )
        st.plotly_chart(fig_slvl, use_container_width=False)

        # --- Volume Heatmap by Hour and Weekday
        st.markdown("### 🔥 Call Volume Heatmap by Hour and Weekday")
        heat_df = df_filtered.groupby(['PERIOD', 'WEEKDAY', 'HOUR'])['CALLS'].sum().reset_index()
        for period in heat_df['PERIOD'].unique():
            st.markdown(f"#### 📅 {period} Period")
            fig_heat = px.density_heatmap(
                heat_df[heat_df['PERIOD'] == period],
                x='HOUR', y='WEEKDAY', z='CALLS',
                color_continuous_scale='Blues',
                title=f"{period} - Calls by Hour & Day",
                width=1000, height=500
            )
            st.plotly_chart(fig_heat, use_container_width=False)

        # --- Stacked Bar for Abandonment
        st.markdown("### 📊 Total vs Abandoned Calls per Day (Stacked View)")
        stack_df = daily.copy()
        stack_df['Non-Abandoned Calls'] = stack_df['TOTAL_CALLS'] - stack_df['ABANDONED']
        stack_df = stack_df.melt(
            id_vars=['DATE', 'PERIOD'],
            value_vars=['ABANDONED', 'Non-Abandoned Calls'],
            var_name='Type',
            value_name='Count'
        )
        stack_df['ColorKey'] = stack_df['PERIOD'] + ' - ' + stack_df['Type']
        custom_color_map = {
            'Before - ABANDONED': '#fca5a5',
            'Before - Non-Abandoned Calls': '#bfdbfe',
            'Current - ABANDONED': '#dc2626',
            'Current - Non-Abandoned Calls': '#3b82f6',
        }
        fig_stack = px.bar(
            stack_df, x='DATE', y='Count', color='ColorKey',
            color_discrete_map=custom_color_map,
            title="Total vs Abandoned Calls per Day (Stacked)",
            height=600, width=1000
        )
        fig_stack.update_layout(barmode='stack')
        st.plotly_chart(fig_stack, use_container_width=False)

        # --- Hourly Aggregation
        st.markdown("### ⏱️ Hourly Metrics (Combined View)")
        hourly = df_filtered.groupby(['HOUR', 'PERIOD']).agg(
            TOTAL_CALLS=('CALLS', 'sum'),
            ABANDONED=('ABANDONED count', 'sum')
        ).reset_index()
        hourly_df = hourly.melt(
            id_vars=['HOUR', 'PERIOD'],
            value_vars=['TOTAL_CALLS', 'ABANDONED'],
            var_name='Type', value_name='Count'
        )
        fig_hourly = px.bar(
            hourly_df, x='HOUR', y='Count', color='PERIOD',
            barmode='group', facet_row='Type',
            title="Hourly Call vs Abandonment (Before vs Current)",
            height=700, width=1000
        )
        st.plotly_chart(fig_hourly, use_container_width=False)

    except Exception as e:
        st.error(f"⚠️ Error loading data: {e}")
        st.info("Make sure your folders and files are valid and correctly formatted.")
