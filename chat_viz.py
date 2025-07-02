import streamlit as st
import pandas as pd
import plotly.express as px
import os

def run_chat_dashboard():

    # --- CONFIG ---
    DATA_DIR_CURRENT = "Filtered/SLA_Chat Hourly"
    DATA_DIR_BEFORE = "Filtered_before/SLA_Chat Hourly"

    # --- Helper: Convert HH:MM:SS to seconds
    def to_seconds(time_str):
        try:
            return pd.to_timedelta(time_str).total_seconds()
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
    st.title("📊 SLA Chat Hourly Dashboard")

    try:
        df = load_with_period_tag()

        # --- Time conversions
        df['CHAT QUEUE TIME (s)'] = df['CHAT QUEUE TIME'].apply(to_seconds)
        df['HANDLE TIME (s)'] = df['HANDLE TIME'].apply(to_seconds)
        df['AFTER CHAT WORK (s)'] = df['AFTER CHAT WORK'].apply(to_seconds)
        df['DATE'] = pd.to_datetime(df['DATE'], dayfirst=True)

        # --- Flags & Labels
        df['IS_ABANDONED'] = df['DISPOSITION'].str.contains('Unresolved|Unresponsive', case=False, na=False)
        df['IS_RESOLVED'] = ~df['IS_ABANDONED']
        df['WEEKDAY'] = df['DATE'].dt.day_name()

        def get_peak_label(hour_str):
            hour = int(str(hour_str).split(":")[0])
            return 'Peak' if 9 <= hour <= 18 else 'Off-Peak'

        df['PEAK_LABEL'] = df['HOUR'].apply(get_peak_label)

        # --- Sidebar Filters
        st.sidebar.header("🔎 Filters")
        if st.sidebar.button("🔄 Reset All Filters"):
            st.experimental_rerun()

        selected_periods = st.sidebar.multiselect("Dataset Period", ['Current', 'Before'], default=['Current', 'Before'])
        df = df[df['PERIOD'].isin(selected_periods)]

        skill_filter = st.sidebar.multiselect("Skill", df['SKILL'].unique(), default=df['SKILL'].unique())
        campaign_filter = st.sidebar.multiselect("Campaign", df['CAMPAIGN'].unique(), default=df['CAMPAIGN'].unique())

        min_date = df['DATE'].min()
        max_date = df['DATE'].max()
        date_range = st.sidebar.date_input("Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

        hour_options = sorted(df['HOUR'].unique(), key=lambda x: int(str(x).split(":")[0]))
        hour_filter = st.sidebar.multiselect("Hour(s)", hour_options, default=hour_options)

        weekday_options = list(df['WEEKDAY'].unique())
        weekday_filter = st.sidebar.multiselect("Weekday(s)", weekday_options, default=weekday_options)

        peak_filter = st.sidebar.multiselect("Time Type", ['Peak', 'Off-Peak'], default=['Peak', 'Off-Peak'])

        df_filtered = df[
            df['SKILL'].isin(skill_filter) &
            df['CAMPAIGN'].isin(campaign_filter) &
            df['HOUR'].isin(hour_filter) &
            df['WEEKDAY'].isin(weekday_filter) &
            df['PEAK_LABEL'].isin(peak_filter) &
            df['DATE'].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]))
        ]

        # --- Daily Aggregation for Scorecard
        daily = df_filtered.groupby(['DATE', 'PERIOD']).agg(
            TOTAL_CHATS=('INTERACTIONS', 'sum'),
            TOTAL_ABANDONED=('IS_ABANDONED', 'sum'),
            TOTAL_RESOLVED=('IS_RESOLVED', 'sum'),
            AVG_QUEUE_TIME=('CHAT QUEUE TIME (s)', 'mean'),
            AVG_HANDLE_TIME=('HANDLE TIME (s)', 'mean'),
            AVG_ACW=('AFTER CHAT WORK (s)', 'mean')
        ).reset_index()
        daily['% ABANDONED'] = (daily['TOTAL_ABANDONED'] / daily['TOTAL_CHATS']) * 100

        # --- Scorecard Metrics (aggregated by period)
        st.markdown("### 📌 Summary Metrics by Period")
        summary = df_filtered.groupby('PERIOD').agg(
            TOTAL_CHATS=('INTERACTIONS', 'sum'),
            TOTAL_ABANDONED=('IS_ABANDONED', 'sum'),
            TOTAL_RESOLVED=('IS_RESOLVED', 'sum'),
            AVG_QUEUE=('CHAT QUEUE TIME (s)', 'mean'),
            AVG_HANDLE=('HANDLE TIME (s)', 'mean'),
            AVG_ACW=('AFTER CHAT WORK (s)', 'mean'),
            MAX_Q=('CHAT QUEUE TIME (s)', 'max'),
            MIN_Q=('CHAT QUEUE TIME (s)', 'min')
        ).reset_index()
        summary['% ABANDONED'] = (summary['TOTAL_ABANDONED'] / summary['TOTAL_CHATS']) * 100
        summary['% RESOLVED'] = (summary['TOTAL_RESOLVED'] / summary['TOTAL_CHATS']) * 100

        for _, row in summary.iterrows():
            st.markdown(f"#### 📅 {row['PERIOD']} Period")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💬 Total Chats", f"{int(row['TOTAL_CHATS']):,}")
                st.metric("🚫 Abandoned", f"{int(row['TOTAL_ABANDONED']):,}")
                st.metric("✅ Resolved", f"{int(row['TOTAL_RESOLVED']):,}")
            with col2:
                st.metric("⏳ Avg Queue Time", f"{row['AVG_QUEUE'] / 60:.2f} mins")
                st.metric("🕒 Avg Handle Time", f"{row['AVG_HANDLE'] / 60:.2f} mins")
                st.metric("🧾 Avg ACW", f"{row['AVG_ACW'] / 60:.2f} mins")
            with col3:
                st.metric("📉 % Abandoned", f"{row['% ABANDONED']:.1f}%")
                st.metric("💯 Resolution Rate", f"{row['% RESOLVED']:.1f}%")
                st.metric("⏱️ Max Queue Time", f"{row['MAX_Q'] / 60:.2f} mins")
                st.metric("⏱️ Min Queue Time", f"{row['MIN_Q'] / 60:.2f} mins")

        # --- Abandonment % Trend by Period
        st.markdown("### 📉 Abandonment Rate Over Time by Period")
        fig_abandon_compare = px.line(
            daily,
            x='DATE',
            y='% ABANDONED',
            color='PERIOD',
            title="Abandonment % Over Time by Dataset Period",
            markers=True,
            width=1000,
            height=400
        )
        st.plotly_chart(fig_abandon_compare, use_container_width=False)

        # --- ACW Trend by Period
        st.markdown("### 🧾 Average ACW Trend by Period")
        fig_acw = px.line(
            daily,
            x='DATE',
            y='AVG_ACW',
            color='PERIOD',
            title="Average After Chat Work Over Time",
            markers=True,
            labels={'AVG_ACW': 'ACW (s)'},
            width=1000,
            height=400
        )
        st.plotly_chart(fig_acw, use_container_width=False)

        # --- Heatmap Comparison
        st.markdown("### 🔥 Chat Volume Heatmap (Day vs Hour) per Period")
        heat_df = df_filtered.groupby(['PERIOD', 'WEEKDAY', 'HOUR'])['INTERACTIONS'].sum().reset_index()

        for period in heat_df['PERIOD'].unique():
            st.markdown(f"#### 📅 {period} Period")
            fig_heat = px.density_heatmap(
                heat_df[heat_df['PERIOD'] == period],
                x='HOUR',
                y='WEEKDAY',
                z='INTERACTIONS',
                color_continuous_scale='Blues',
                title=f"{period} - Chat Volume by Hour & Weekday",
                width=1000,
                height=500
            )
            st.plotly_chart(fig_heat, use_container_width=False)

        # --- Total vs Abandoned Chats per Day (Stacked View)
        st.markdown("### 📊 Total vs Abandoned Chats per Day (Stacked View)")

        # Create base + abandoned stacked values
        stack_df = daily.copy()
        stack_df['Non-Abandoned Chats'] = stack_df['TOTAL_CHATS'] - stack_df['TOTAL_ABANDONED']

        # Melt for stacked format (Abandoned first to appear on bottom)
        stack_df = stack_df.melt(
            id_vars=['DATE', 'PERIOD'],
            value_vars=['TOTAL_ABANDONED', 'Non-Abandoned Chats'],  # Order matters!
            var_name='Type',
            value_name='Count'
        )

        # Create combined label for color mapping
        stack_df['ColorKey'] = stack_df['PERIOD'] + ' - ' + stack_df['Type']

        # Custom color mapping
        custom_color_map = {
        'Before - TOTAL_ABANDONED': '#fca5a5',       # Light red
        'Before - Non-Abandoned Chats': '#bfdbfe',   # Light blue
        'Current - TOTAL_ABANDONED': '#dc2626',      # Deep red
        'Current - Non-Abandoned Chats': '#3b82f6'   # Vivid blue
    }

        # Plot stacked bar chart
        fig_stacked = px.bar(
            stack_df,
            x='DATE',
            y='Count',
            color='ColorKey',
            color_discrete_map=custom_color_map,
            title="Total vs Abandoned Chats per Day (Stacked View)",
            labels={'ColorKey': 'Period & Type'},
            height=600,
            width=1000,
        )

        fig_stacked.update_layout(barmode='stack')
        st.plotly_chart(fig_stacked, use_container_width=False)

        # --- Prepare Hourly Aggregation
        hourly = df_filtered.groupby(['HOUR', 'PERIOD']).agg(
            TOTAL_CHATS=('INTERACTIONS', 'sum'),
            TOTAL_ABANDONED=('IS_ABANDONED', 'sum')
        ).reset_index()

        # --- Hourly Aggregation (Combined View)
        st.markdown("### ⏱️ Hourly Aggregated Metrics (Combined View)")

        hourly_chart_df = hourly.melt(
            id_vars=['HOUR', 'PERIOD'],
            value_vars=['TOTAL_ABANDONED', 'TOTAL_CHATS'],
            var_name='Type',
            value_name='Count'
        )

        fig_hourly_combined = px.bar(
            hourly_chart_df,
            x='HOUR',
            y='Count',
            color='PERIOD',
            barmode='group',
            facet_row='Type',
            title="Total vs Abandoned Chats per Hour (Before vs Current)",
            text_auto=True,
            height=700,
            width=1000
        )
        fig_hourly_combined.update_yaxes(range=[0, 30000])
        st.plotly_chart(fig_hourly_combined, use_container_width=False)



    except Exception as e:
        st.error(f"⚠️ Error loading CSVs: {e}")
        st.info("Make sure the folders exist and contain valid CSV files.")
