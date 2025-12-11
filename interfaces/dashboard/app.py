"""
PROJECT_HIVE Enterprise Dashboard - Streamlit Application
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.telemetry.metrics import metrics
from observability.session_replay import session_replay

# Page configuration
st.set_page_config(
    page_title="PROJECT_HIVE Dashboard",
    page_icon="🐝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2563EB;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #F3F4F6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3B82F6;
        margin-bottom: 1rem;
    }
    .status-running { color: #10B981; font-weight: bold; }
    .status-completed { color: #3B82F6; font-weight: bold; }
    .status-failed { color: #EF4444; font-weight: bold; }
    .agent-card {
        background-color: #FEF3C7;
        padding: 0.75rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        border: 1px solid #FBBF24;
    }
</style>
""", unsafe_allow_html=True)


class HiveDashboard:
    """Main dashboard application."""

    def __init__(self):
        self.data_dir = Path("data")
        self.sessions_dir = self.data_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def render_sidebar(self):
        """Render the sidebar navigation."""
        with st.sidebar:
            st.image("https://img.icons8.com/color/96/000000/bee.png", width=80)
            st.markdown("<div class='main-header'>PROJECT_HIVE</div>", unsafe_allow_html=True)
            st.markdown("**Enterprise AI Orchestration Platform**")

            st.divider()

            # Navigation
            page = st.radio(
                "Navigation",
                ["🏠 Dashboard", "📊 Metrics", "🔍 Session Explorer",
                 "🚀 Pipeline Runner", "⚙️ Settings"]
            )

            st.divider()

            # Quick stats
            st.markdown("**Quick Stats**")

            # Get session count
            sessions = session_replay.list_sessions(limit=1000)
            running_sessions = [s for s in sessions if s.get("status") == "running"]

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Sessions", len(sessions))
            with col2:
                st.metric("Active", len(running_sessions))

            st.divider()

            # System status
            st.markdown("**System Status**")
            st.success("✅ Operational")

            return page

    def render_dashboard(self):
        """Render the main dashboard page."""
        st.markdown("<div class='main-header'>🏠 System Dashboard</div>", unsafe_allow_html=True)

        # Get recent sessions
        sessions = session_replay.list_sessions(limit=10)

        # Top row: Key metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            with st.container():
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.metric("Total Pipeline Runs", len(sessions))
                st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            success_count = len([s for s in sessions if s.get("status") == "completed"])
            with st.container():
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.metric("Success Rate",
                          f"{(success_count / len(sessions) * 100):.1f}%" if sessions else "0%")
                st.markdown("</div>", unsafe_allow_html=True)

        with col3:
            # Calculate average events per session
            avg_events = 0
            if sessions:
                total_events = sum(s.get("event_count", 0) for s in sessions)
                avg_events = total_events / len(sessions)
            with st.container():
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.metric("Avg Events/Session", f"{avg_events:.1f}")
                st.markdown("</div>", unsafe_allow_html=True)

        with col4:
            with st.container():
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                # Get active agents from metrics
                metrics_summary = metrics.get_metrics_summary()
                active_agents = metrics_summary.get("hive_active_agents", {}).get("values", {})
                active_count = list(active_agents.values())[0] if active_agents else 0
                st.metric("Active Agents", active_count)
                st.markdown("</div>", unsafe_allow_html=True)

        # Middle row: Recent sessions and activity chart
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("<div class='sub-header'>📈 Activity Timeline</div>", unsafe_allow_html=True)
            self._render_activity_timeline(sessions)

        with col2:
            st.markdown("<div class='sub-header'>📋 Recent Sessions</div>", unsafe_allow_html=True)
            self._render_recent_sessions(sessions)

        # Bottom row: Agent performance
        st.markdown("<div class='sub-header'>🤖 Agent Performance</div>", unsafe_allow_html=True)
        self._render_agent_performance()

    def _render_activity_timeline(self, sessions):
        """Render activity timeline chart."""
        if not sessions:
            st.info("No sessions yet. Run a pipeline to see activity.")
            return

        # Create timeline data
        timeline_data = []
        for session in sessions:
            try:
                start_time = datetime.fromisoformat(session["start_time"].replace('Z', '+00:00'))
                timeline_data.append({
                    "time": start_time,
                    "session_id": session["session_id"],
                    "goal": session["goal"][:50] + "..." if len(session["goal"]) > 50 else session["goal"],
                    "status": session.get("status", "unknown"),
                    "events": session.get("event_count", 0)
                })
            except (ValueError, KeyError):
                continue

        if not timeline_data:
            st.warning("Could not parse session timeline data")
            return

        df = pd.DataFrame(timeline_data)

        # Create timeline chart
        fig = go.Figure()

        # Add scatter points for each session
        for status in df["status"].unique():
            status_df = df[df["status"] == status]

            # Map status to colors
            color_map = {
                "running": "#10B981",
                "completed": "#3B82F6",
                "failed": "#EF4444",
                "unknown": "#6B7280"
            }

            fig.add_trace(go.Scatter(
                x=status_df["time"],
                y=[1] * len(status_df),  # Constant y-value for timeline
                mode="markers",
                name=status,
                marker=dict(
                    size=status_df["events"] / 2 + 10,  # Size based on event count
                    color=color_map.get(status, "#6B7280"),
                    line=dict(width=2, color="white")
                ),
                text=status_df.apply(
                    lambda row: f"<b>{row['goal']}</b><br>"
                                f"Status: {row['status']}<br>"
                                f"Events: {row['events']}<br>"
                                f"Time: {row['time'].strftime('%Y-%m-%d %H:%M')}",
                    axis=1
                ),
                hoverinfo="text",
                customdata=status_df["session_id"]
            ))

        # Update layout
        fig.update_layout(
            title="Pipeline Activity Timeline",
            xaxis_title="Time",
            yaxis=dict(showticklabels=False, showgrid=False),
            height=300,
            hovermode="closest",
            plot_bgcolor="white",
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

    def _render_recent_sessions(self, sessions):
        """Render list of recent sessions."""
        if not sessions:
            st.info("No sessions found")
            return

        for session in sessions[:5]:  # Show only 5 most recent
            with st.container():
                # Status color coding
                status = session.get("status", "unknown")
                status_color = {
                    "running": "🟢",
                    "completed": "🔵",
                    "failed": "🔴",
                    "unknown": "⚪"
                }.get(status, "⚪")

                col1, col2 = st.columns([1, 4])
                with col1:
                    st.markdown(f"**{status_color}**")
                with col2:
                    goal = session["goal"]
                    if len(goal) > 40:
                        goal = goal[:40] + "..."

                    if st.button(f"{goal}", key=f"session_{session['session_id']}"):
                        st.session_state.selected_session = session['session_id']
                        st.rerun()

                    # Session info
                    st.caption(f"📅 {session['start_time'][:10]} | "
                               f"📊 {session.get('event_count', 0)} events")

    def _render_agent_performance(self):
        """Render agent performance metrics."""
        # Get metrics summary
        metrics_summary = metrics.get_metrics_summary()

        # Extract agent metrics
        agent_data = []
        for metric_name, metric_info in metrics_summary.items():
            if "agent" in metric_name and "executions" in metric_name:
                if isinstance(metric_info.get("values"), dict):
                    for labels, value in metric_info["values"].items():
                        if isinstance(labels, tuple):
                            # Parse labels
                            labels_dict = dict(labels)
                            agent_name = labels_dict.get("agent_name", "unknown")
                            status = labels_dict.get("status", "unknown")

                            if status == "success":
                                agent_data.append({
                                    "agent": agent_name,
                                    "executions": value,
                                    "metric": metric_name
                                })

        if not agent_data:
            st.info("No agent performance data available yet")
            return

        # Create DataFrame and aggregate
        df = pd.DataFrame(agent_data)
        if not df.empty:
            agent_stats = df.groupby("agent").agg({"executions": "sum"}).reset_index()

            # Create bar chart
            fig = px.bar(
                agent_stats,
                x="agent",
                y="executions",
                title="Agent Execution Count",
                color="executions",
                color_continuous_scale="Viridis"
            )

            fig.update_layout(
                height=300,
                xaxis_title="Agent",
                yaxis_title="Executions",
                plot_bgcolor="white"
            )

            st.plotly_chart(fig, use_container_width=True)

    def render_metrics_page(self):
        """Render the metrics monitoring page."""
        st.markdown("<div class='main-header'>📊 System Metrics</div>", unsafe_allow_html=True)

        # Prometheus metrics endpoint info
        st.info("""
        Prometheus metrics are available at `/metrics` endpoint when running the API.
        Use this page for real-time dashboard monitoring.
        """)

        # Get metrics summary
        metrics_summary = metrics.get_metrics_summary()

        # Tabs for different metric categories
        tab1, tab2, tab3, tab4 = st.tabs([
            "👥 Agent Metrics",
            "⚡ Performance",
            "💰 Budget",
            "🔧 System"
        ])

        with tab1:
            self._render_agent_metrics(metrics_summary)

        with tab2:
            self._render_performance_metrics(metrics_summary)

        with tab3:
            self._render_budget_metrics(metrics_summary)

        with tab4:
            self._render_system_metrics(metrics_summary)

    def _render_agent_metrics(self, metrics_summary):
        """Render agent-specific metrics."""
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Agent Executions**")
            agent_exec_data = []
            for name, info in metrics_summary.items():
                if "agent_executions_total" in name and info.get("values"):
                    for labels, value in info["values"].items():
                        if isinstance(labels, tuple):
                            labels_dict = dict(labels)
                            agent_exec_data.append({
                                "agent": labels_dict.get("agent_name", "unknown"),
                                "status": labels_dict.get("status", "unknown"),
                                "count": value
                            })

            if agent_exec_data:
                df = pd.DataFrame(agent_exec_data)
                pivot_df = df.pivot_table(
                    index="agent",
                    columns="status",
                    values="count",
                    fill_value=0
                ).reset_index()

                st.dataframe(pivot_df, use_container_width=True)
            else:
                st.info("No agent execution data yet")

        with col2:
            st.markdown("**Agent Duration**")
            # Find duration metrics
            duration_data = []
            for name, info in metrics_summary.items():
                if "agent_execution_duration" in name and info.get("values"):
                    for labels, values in info["values"].items():
                        if isinstance(values, list) and values:
                            labels_dict = dict(labels) if isinstance(labels, tuple) else {}
                            avg_duration = sum(values) / len(values)
                            duration_data.append({
                                "agent": labels_dict.get("agent_name", "unknown"),
                                "avg_duration_ms": avg_duration
                            })

            if duration_data:
                df = pd.DataFrame(duration_data)
                fig = px.bar(
                    df,
                    x="agent",
                    y="avg_duration_ms",
                    title="Average Execution Duration (ms)"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No duration data yet")

    def _render_performance_metrics(self, metrics_summary):
        """Render performance metrics."""
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**LLM Performance**")
            llm_data = []
            for name, info in metrics_summary.items():
                if "llm_calls_total" in name and info.get("values"):
                    for labels, value in info["values"].items():
                        if isinstance(labels, tuple):
                            labels_dict = dict(labels)
                            llm_data.append({
                                "provider": labels_dict.get("provider", "unknown"),
                                "model": labels_dict.get("model", "unknown"),
                                "calls": value
                            })

            if llm_data:
                df = pd.DataFrame(llm_data)
                if not df.empty:
                    fig = px.sunburst(
                        df,
                        path=['provider', 'model'],
                        values='calls',
                        title="LLM Calls Distribution"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No LLM call data yet")

        with col2:
            st.markdown("**Pipeline Performance**")
            pipeline_data = []
            for name, info in metrics_summary.items():
                if "pipeline_duration" in name and info.get("values"):
                    for labels, values in info["values"].items():
                        if isinstance(values, list) and values:
                            labels_dict = dict(labels) if isinstance(labels, tuple) else {}
                            pipeline_type = labels_dict.get("pipeline_type", "unknown")
                            for duration in values:
                                pipeline_data.append({
                                    "pipeline": pipeline_type,
                                    "duration": duration
                                })

            if pipeline_data:
                df = pd.DataFrame(pipeline_data)
                if not df.empty:
                    fig = px.box(
                        df,
                        x="pipeline",
                        y="duration",
                        title="Pipeline Duration Distribution"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No pipeline duration data yet")

    def _render_budget_metrics(self, metrics_summary):
        """Render budget and cost metrics."""
        st.markdown("**Budget Usage**")

        budget_data = []
        for name, info in metrics_summary.items():
            if "budget_" in name and info.get("values"):
                for labels, value in info["values"].items():
                    if isinstance(labels, tuple):
                        labels_dict = dict(labels)
                        budget_data.append({
                            "metric": name.replace("hive_", ""),
                            "tenant": labels_dict.get("tenant_id", "default"),
                            "value": value
                        })

        if budget_data:
            df = pd.DataFrame(budget_data)

            # Create gauge charts for budget
            col1, col2 = st.columns(2)

            with col1:
                used_budget = df[df["metric"] == "budget_used_usd"]["value"].sum()
                st.metric("Total Budget Used", f"${used_budget:.2f}")

                # Simple gauge chart
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=used_budget,
                    title={"text": "Budget Used"},
                    gauge={
                        "axis": {"range": [None, 100]},
                        "bar": {"color": "darkblue"},
                        "steps": [
                            {"range": [0, 50], "color": "lightgreen"},
                            {"range": [50, 80], "color": "yellow"},
                            {"range": [80, 100], "color": "red"}
                        ]
                    }
                ))
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                remaining_budget = df[df["metric"] == "budget_remaining_usd"]["value"].sum()
                st.metric("Budget Remaining", f"${remaining_budget:.2f}")

                # Remaining budget pie chart
                if used_budget + remaining_budget > 0:
                    fig = px.pie(
                        values=[used_budget, remaining_budget],
                        names=["Used", "Remaining"],
                        title="Budget Distribution",
                        color=["Used", "Remaining"],
                        color_discrete_map={"Used": "#EF4444", "Remaining": "#10B981"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No budget data available yet")

    def _render_system_metrics(self, metrics_summary):
        """Render system-level metrics."""
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Queue Status**")
            queue_data = []
            for name, info in metrics_summary.items():
                if "queue_size" in name and info.get("values"):
                    for labels, value in info["values"].items():
                        if isinstance(labels, tuple):
                            labels_dict = dict(labels)
                            queue_data.append({
                                "queue": labels_dict.get("queue_name", "unknown"),
                                "size": value
                            })

            if queue_data:
                df = pd.DataFrame(queue_data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No queue data")

        with col2:
            st.markdown("**Self-Healing**")
            healing_data = []
            for name, info in metrics_summary.items():
                if "self_healing" in name and info.get("values"):
                    for labels, value in info["values"].items():
                        if isinstance(labels, tuple):
                            labels_dict = dict(labels)
                            healing_data.append({
                                "type": labels_dict.get("error_type", "unknown"),
                                "success": labels_dict.get("success", "unknown"),
                                "count": value
                            })

            if healing_data:
                df = pd.DataFrame(healing_data)
                success_rate = 0
                if not df.empty:
                    total = df["count"].sum()
                    successful = df[df["success"] == "True"]["count"].sum()
                    success_rate = (successful / total * 100) if total > 0 else 0

                st.metric("Self-Healing Success Rate", f"{success_rate:.1f}%")
            else:
                st.info("No self-healing data")

        with col3:
            st.markdown("**Active Components**")
            active_agents = 0
            for name, info in metrics_summary.items():
                if "active_agents" in name and info.get("values"):
                    active_agents = list(info["values"].values())[0] if info["values"] else 0

            st.metric("Active Agents", active_agents)

    def render_session_explorer(self):
        """Render the session explorer page."""
        st.markdown("<div class='main-header'>🔍 Session Explorer</div>", unsafe_allow_html=True)

        # Session selection
        sessions = session_replay.list_sessions(limit=100)

        col1, col2 = st.columns([2, 1])

        with col1:
            if sessions:
                # Create a select box with session details
                session_options = {
                    f"{s['session_id'][:8]}... - {s['goal'][:50]}": s['session_id']
                    for s in sessions
                }

                selected_option = st.selectbox(
                    "Select a session to explore:",
                    options=list(session_options.keys()),
                    index=0
                )

                selected_session_id = session_options[selected_option]
            else:
                st.info("No sessions available")
                selected_session_id = None

        with col2:
            st.markdown("**Quick Actions**")
            if selected_session_id and st.button("🎬 Replay Session", use_container_width=True):
                st.session_state.replay_session = selected_session_id

            if st.button("📊 View Statistics", use_container_width=True):
                if selected_session_id:
                    stats = session_replay.get_session_statistics(selected_session_id)
                    st.session_state.session_stats = stats

        if selected_session_id:
            # Get session details
            session_details = session_replay.get_session(selected_session_id)

            if session_details:
                # Session header
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Session ID:** `{session_details['session_id']}`")
                with col2:
                    status = session_details.get("status", "unknown")
                    status_class = f"status-{status}"
                    st.markdown(f"<div class='{status_class}'>**Status:** {status}</div>",
                                unsafe_allow_html=True)
                with col3:
                    st.markdown(f"**Events:** {len(session_details.get('events', []))}")

                st.markdown(f"**Goal:** {session_details['goal']}")

                # Tabs for different views
                tab1, tab2, tab3, tab4 = st.tabs([
                    "📋 Events",
                    "📈 Timeline",
                    "🤖 Agent Activity",
                    "📁 Artifacts"
                ])

                with tab1:
                    self._render_session_events(session_details)

                with tab2:
                    self._render_session_timeline(session_details)

                with tab3:
                    self._render_agent_activity(session_details)

                with tab4:
                    self._render_session_artifacts(session_details)

            # Replay session if requested
            if hasattr(st.session_state, 'replay_session'):
                if st.session_state.replay_session == selected_session_id:
                    self._render_session_replay(selected_session_id)

            # Show statistics if requested
            if hasattr(st.session_state, 'session_stats'):
                self._render_session_statistics(st.session_state.session_stats)

    def _render_session_events(self, session_details):
        """Render session events in a table."""
        events = session_details.get("events", [])

        if not events:
            st.info("No events recorded for this session")
            return

        # Create DataFrame for events
        event_data = []
        for event in events:
            event_data.append({
                "Timestamp": event.get("timestamp", "")[:19],
                "Type": event.get("event_type", ""),
                "Agent": event.get("agent_name", ""),
                "Duration (ms)": event.get("duration_ms", ""),
                "Details": json.dumps(event.get("data", {}), indent=2)[:100] + "..."
                if event.get("data") else ""
            })

        df = pd.DataFrame(event_data)
        st.dataframe(df, use_container_width=True, height=400)

        # Event details expander
        with st.expander("View Raw Event Data"):
            selected_event = st.selectbox(
                "Select event to view details:",
                range(len(events)),
                format_func=lambda i: f"Event {i + 1}: {events[i].get('event_type', 'unknown')}"
            )

            if 0 <= selected_event < len(events):
                st.json(events[selected_event])

    def _render_session_timeline(self, session_details):
        """Render session timeline visualization."""
        events = session_details.get("events", [])

        if not events:
            st.info("No events to display on timeline")
            return

        # Create timeline data
        timeline_data = []
        for i, event in enumerate(events):
            try:
                timestamp = datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
                timeline_data.append({
                    "Event": f"Event {i + 1}",
                    "Timestamp": timestamp,
                    "Type": event.get("event_type", "unknown"),
                    "Agent": event.get("agent_name", "N/A"),
                    "Duration": event.get("duration_ms", 0)
                })
            except (ValueError, KeyError):
                continue

        if not timeline_data:
            st.warning("Could not parse timeline data")
            return

        df = pd.DataFrame(timeline_data)

        # Create Gantt-like chart
        fig = px.timeline(
            df,
            x_start="Timestamp",
            x_end=df["Timestamp"] + pd.to_timedelta(df["Duration"], unit='ms'),
            y="Event",
            color="Type",
            hover_data=["Agent", "Duration"],
            title="Session Timeline"
        )

        fig.update_layout(
            height=500,
            xaxis_title="Time",
            yaxis_title="Event",
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

    def _render_agent_activity(self, session_details):
        """Render agent activity breakdown."""
        events = session_details.get("events", [])

        # Group events by agent
        agent_activity = {}
        for event in events:
            agent_name = event.get("agent_name")
            if agent_name:
                if agent_name not in agent_activity:
                    agent_activity[agent_name] = {
                        "count": 0,
                        "total_duration": 0,
                        "event_types": set()
                    }

                agent_activity[agent_name]["count"] += 1
                if event.get("duration_ms"):
                    agent_activity[agent_name]["total_duration"] += event.get("duration_ms")
                agent_activity[agent_name]["event_types"].add(event.get("event_type", "unknown"))

        if not agent_activity:
            st.info("No agent activity recorded")
            return

        # Display agent cards
        for agent_name, stats in agent_activity.items():
            with st.container():
                st.markdown("<div class='agent-card'>", unsafe_allow_html=True)

                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"**{agent_name}**")
                with col2:
                    st.markdown(f"📊 {stats['count']} events")
                with col3:
                    avg_duration = stats['total_duration'] / stats['count'] if stats['count'] > 0 else 0
                    st.markdown(f"⏱️ {avg_duration:.0f}ms avg")

                # Event types
                event_types = ", ".join(sorted(stats['event_types']))
                st.caption(f"Event types: {event_types}")

                st.markdown("</div>", unsafe_allow_html=True)

        # Agent performance chart
        agent_names = list(agent_activity.keys())
        event_counts = [stats["count"] for stats in agent_activity.values()]
        avg_durations = [
            stats["total_duration"] / stats["count"] if stats["count"] > 0 else 0
            for stats in agent_activity.values()
        ]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=agent_names,
            y=event_counts,
            name="Event Count",
            yaxis="y",
            marker_color="lightblue"
        ))

        fig.add_trace(go.Scatter(
            x=agent_names,
            y=avg_durations,
            name="Avg Duration (ms)",
            yaxis="y2",
            line=dict(color="red", width=2)
        ))

        fig.update_layout(
            title="Agent Activity",
            yaxis=dict(title="Event Count"),
            yaxis2=dict(
                title="Avg Duration (ms)",
                overlaying="y",
                side="right"
            ),
            height=400,
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

    def _render_session_artifacts(self, session_details):
        """Render session artifacts."""
        # Look for artifacts in events
        artifacts = []
        for event in session_details.get("events", []):
            data = event.get("data", {})
            if "artifacts" in data:
                for key, value in data["artifacts"].items():
                    if isinstance(value, dict) and value.get("artifact_type"):
                        artifacts.append({
                            "event": event.get("event_type"),
                            "artifact": key,
                            "type": value.get("artifact_type"),
                            "timestamp": event.get("timestamp")
                        })

        if artifacts:
            df = pd.DataFrame(artifacts)
            st.dataframe(df, use_container_width=True)

            # Show artifact details
            selected_artifact = st.selectbox(
                "Select artifact to view:",
                df["artifact"].unique()
            )

            # Find and display the artifact
            for event in session_details.get("events", []):
                data = event.get("data", {})
                if "artifacts" in data and selected_artifact in data["artifacts"]:
                    artifact_data = data["artifacts"][selected_artifact]
                    with st.expander(f"Artifact: {selected_artifact}"):
                        st.json(artifact_data)
                    break
        else:
            st.info("No artifacts recorded in this session")

    def _render_session_replay(self, session_id):
        """Render session replay interface."""
        st.markdown("---")
        st.markdown("<div class='sub-header'>🎬 Session Replay</div>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            replay_speed = st.slider("Playback Speed", 0.25, 4.0, 1.0, 0.25)
        with col2:
            if st.button("▶️ Start Replay", use_container_width=True):
                st.session_state.replay_in_progress = True
                st.session_state.replay_index = 0
        with col3:
            if st.button("⏹️ Stop Replay", use_container_width=True):
                st.session_state.replay_in_progress = False

        # Replay display area
        replay_placeholder = st.empty()

        if hasattr(st.session_state, 'replay_in_progress') and st.session_state.replay_in_progress:
            # Start async replay
            import asyncio

            async def run_replay():
                session = session_replay.get_session(session_id)
                if not session:
                    return

                events = session.get("events", [])
                for i, event in enumerate(events[:50]):  # Limit for demo
                    with replay_placeholder.container():
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            progress = (i + 1) / len(events)
                            st.progress(progress)
                            st.metric("Event", f"{i + 1}/{len(events)}")

                        with col2:
                            st.markdown(f"**{event.get('event_type', 'Unknown')}**")
                            if event.get('agent_name'):
                                st.markdown(f"*Agent:* {event['agent_name']}")
                            if event.get('duration_ms'):
                                st.markdown(f"*Duration:* {event['duration_ms']}ms")

                            # Show data preview
                            data = event.get('data', {})
                            if data:
                                with st.expander("View Data"):
                                    st.json(data)

                    await asyncio.sleep(0.5 / replay_speed)  # Simulate time passing

            # Note: Streamlit async support is limited
            st.info("Note: Full async replay requires Streamlit integration")

    def _render_session_statistics(self, stats):
        """Render session statistics."""
        st.markdown("---")
        st.markdown("<div class='sub-header'>📊 Session Statistics</div>", unsafe_allow_html=True)

        if "error" in stats:
            st.error(stats["error"])
            return

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Events", stats.get("total_events", 0))
        with col2:
            st.metric("Agent Events", stats.get("agent_events", 0))
        with col3:
            st.metric("LLM Events", stats.get("llm_events", 0))
        with col4:
            st.metric("Error Events", stats.get("error_events", 0))

        # Duration statistics
        duration_stats = stats.get("duration_stats", {})
        if duration_stats:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Duration", f"{duration_stats.get('total_ms', 0):.0f}ms")
            with col2:
                st.metric("Average", f"{duration_stats.get('average_ms', 0):.0f}ms")
            with col3:
                st.metric("Min", f"{duration_stats.get('min_ms', 0):.0f}ms")
            with col4:
                st.metric("Max", f"{duration_stats.get('max_ms', 0):.0f}ms")

        # Agent statistics table
        agent_stats = stats.get("agent_statistics", {})
        if agent_stats:
            st.markdown("**Agent Performance**")
            agent_data = []
            for agent, agent_stat in agent_stats.items():
                agent_data.append({
                    "Agent": agent,
                    "Executions": agent_stat.get("count", 0),
                    "Total Duration (ms)": agent_stat.get("total_duration_ms", 0),
                    "Errors": agent_stat.get("errors", 0),
                    "Avg Duration (ms)": agent_stat.get("total_duration_ms", 0) / agent_stat.get("count", 1)
                })

            df = pd.DataFrame(agent_data)
            st.dataframe(df, use_container_width=True)

    def render_pipeline_runner(self):
        """Render the pipeline runner page."""
        st.markdown("<div class='main-header'>🚀 Pipeline Runner</div>", unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["🏃 Run Pipeline", "📁 Pipeline Templates"])

        with tab1:
            self._render_pipeline_runner()

        with tab2:
            self._render_pipeline_templates()

    def _render_pipeline_runner(self):
        """Render pipeline runner interface."""
        col1, col2 = st.columns([2, 1])

        with col1:
            # Pipeline selection
            pipeline_type = st.selectbox(
                "Select Pipeline Type:",
                ["T1 Fortress (Enterprise)", "T0 Velocity (Fast)"],
                index=0
            )

            # Goal input
            goal = st.text_area(
                "Enter your goal:",
                value="Build a simple calculator application with basic operations",
                height=100
            )

            # Advanced options
            with st.expander("Advanced Options"):
                col_a, col_b = st.columns(2)
                with col_a:
                    max_budget = st.number_input("Max Budget (USD)", 1.0, 100.0, 10.0)
                    timeout = st.number_input("Timeout (seconds)", 30, 3600, 300)
                with col_b:
                    enable_debug = st.checkbox("Enable Debug Mode", True)
                    require_approval = st.checkbox("Require Human Approval", False)

        with col2:
            st.markdown("**Quick Templates**")

            if st.button("📱 Simple API", use_container_width=True):
                st.session_state.preset_goal = "Build a REST API for user management"
                st.rerun()

            if st.button("🔧 CLI Tool", use_container_width=True):
                st.session_state.preset_goal = "Create a command-line tool for file management"
                st.rerun()

            if st.button("📊 Data Analyzer", use_container_width=True):
                st.session_state.preset_goal = "Build a data analysis tool with pandas"
                st.rerun()

            # Apply preset goal if set
            if hasattr(st.session_state, 'preset_goal') and st.session_state.preset_goal is not None:
                goal = st.session_state.preset_goal
                # We don't delete the preset goal here because we want to keep it until the user changes it

        # Run button
        if st.button("🚀 Run Pipeline", type="primary", use_container_width=True):
            with st.spinner("Initializing pipeline..."):
                # Create a unique run ID
                import uuid
                run_id = str(uuid.uuid4())

                # Start session recording
                from observability.session_replay import session_replay, EventType
                session_replay.start_session(
                    session_id=run_id,
                    run_id=run_id,
                    goal=goal,
                    pipeline_type=pipeline_type,
                    metadata={
                        "max_budget": max_budget,
                        "timeout": timeout,
                        "debug_mode": enable_debug,
                        "require_approval": require_approval
                    }
                )

                # Record pipeline start
                session_replay.record_event(
                    session_id=run_id,
                    event_type=EventType.AGENT_START,
                    agent_name="Pipeline",
                    data={"goal": goal, "type": pipeline_type}
                )

                # Store run info in session state
                st.session_state.current_run = {
                    "run_id": run_id,
                    "goal": goal,
                    "pipeline_type": pipeline_type,
                    "status": "running",
                    "start_time": datetime.now().isoformat()
                }

                st.success(f"Pipeline started with Run ID: `{run_id}`")

                # In a real implementation, this would run asynchronously
                st.info("Note: In this demo, pipeline execution is simulated.")

                # Simulate pipeline progress
                progress_bar = st.progress(0)
                status_text = st.empty()

                for i in range(5):
                    progress = (i + 1) / 5
                    progress_bar.progress(progress)

                    steps = [
                        "Researching requirements...",
                        "Designing architecture...",
                        "Generating code...",
                        "Testing implementation...",
                        "Finalizing artifacts..."
                    ]

                    status_text.text(steps[i])

                    # Simulate recording events
                    session_replay.record_event(
                        session_id=run_id,
                        event_type=EventType.AGENT_COMPLETE,
                        agent_name=["Researcher", "Architect", "Developer", "Tester", "Reviewer"][i],
                        data={"step": steps[i], "progress": progress},
                        duration_ms=1000
                    )

                    # Simulate delay
                    import time
                    time.sleep(1)

                # Mark pipeline as completed
                session_replay.record_event(
                    session_id=run_id,
                    event_type=EventType.AGENT_COMPLETE,
                    agent_name="Pipeline",
                    data={"status": "completed", "artifacts_generated": True},
                    duration_ms=5000
                )

                session_replay.end_session(run_id, "completed")

                st.session_state.current_run["status"] = "completed"
                st.session_state.current_run["end_time"] = datetime.now().isoformat()

                st.success("✅ Pipeline completed successfully!")

                # Show results
                with st.expander("View Results"):
                    st.markdown(f"**Run ID:** `{run_id}`")
                    st.markdown(f"**Goal:** {goal}")
                    st.markdown("**Generated Artifacts:**")
                    st.code("""
                    generated_app.py - Main calculator application
                    tests/test_calculator.py - Unit tests
                    README.md - Documentation
                    """)

        # Show current run status if available
        if st.session_state.current_run is not None:
            st.markdown("---")
            st.markdown("**Current Run Status**")

            run = st.session_state.current_run
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"**Run ID:** `{run['run_id'][:8]}...`")
            with col2:
                status = run.get("status", "unknown")
                status_color = {
                    "running": "🟢",
                    "completed": "🔵",
                    "failed": "🔴"
                }.get(status, "⚪")
                st.markdown(f"**Status:** {status_color} {status}")
            with col3:
                if run.get("start_time"):
                    st.markdown(f"**Started:** {run['start_time'][11:19]}")

            if run.get("status") == "completed" and st.button("🔍 Explore This Run"):
                st.session_state.selected_session = run['run_id']
                st.rerun()

    def _render_pipeline_templates(self):
        """Render pipeline templates."""
        st.info("Pipeline templates provide predefined configurations for common tasks.")

        templates = [
            {
                "name": "📱 REST API",
                "description": "Build a complete REST API with authentication",
                "goal": "Create a FastAPI REST API with JWT authentication, user management, and Swagger documentation",
                "estimated_time": "5-10 minutes",
                "complexity": "Medium"
            },
            {
                "name": "🔧 CLI Tool",
                "description": "Create a command-line interface tool",
                "goal": "Build a Python CLI tool with argument parsing, logging, and file operations",
                "estimated_time": "3-5 minutes",
                "complexity": "Low"
            },
            {
                "name": "📊 Data Pipeline",
                "description": "ETL pipeline for data processing",
                "goal": "Design a data pipeline that reads CSV files, processes data with pandas, and exports results",
                "estimated_time": "8-12 minutes",
                "complexity": "High"
            },
            {
                "name": "🤖 Chatbot",
                "description": "Build an AI-powered chatbot",
                "goal": "Create a chatbot using LangChain with memory, tool integration, and streaming responses",
                "estimated_time": "10-15 minutes",
                "complexity": "High"
            },
            {
                "name": "🌐 Web Scraper",
                "description": "Robust web scraping utility",
                "goal": "Build a web scraper with error handling, rate limiting, and data export capabilities",
                "estimated_time": "6-9 minutes",
                "complexity": "Medium"
            }
        ]

        for template in templates:
            with st.container():
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f"### {template['name']}")
                    st.caption(f"⏱️ {template['estimated_time']}")
                    st.caption(f"📊 {template['complexity']}")
                with col2:
                    st.markdown(template['description'])
                    st.markdown(f"**Goal:** {template['goal']}")

                    if st.button(f"Use This Template", key=f"template_{template['name']}"):
                        st.session_state.preset_goal = template['goal']
                        st.rerun()

                st.divider()

    def _render_pipeline_templates(self):
        """Render pipeline templates."""
        st.info("Pipeline templates provide predefined configurations for common tasks.")

        templates = [
            {
                "name": "📱 REST API",
                "description": "Build a complete REST API with authentication",
                "goal": "Create a FastAPI REST API with JWT authentication, user management, and Swagger documentation",
                "estimated_time": "5-10 minutes",
                "complexity": "Medium"
            },
            {
                "name": "🔧 CLI Tool",
                "description": "Create a command-line interface tool",
                "goal": "Build a Python CLI tool with argument parsing, logging, and file operations",
                "estimated_time": "3-5 minutes",
                "complexity": "Low"
            },
            {
                "name": "📊 Data Pipeline",
                "description": "ETL pipeline for data processing",
                "goal": "Design a data pipeline that reads CSV files, processes data with pandas, and exports results",
                "estimated_time": "8-12 minutes",
                "complexity": "High"
            },
            {
                "name": "🤖 Chatbot",
                "description": "Build an AI-powered chatbot",
                "goal": "Create a chatbot using LangChain with memory, tool integration, and streaming responses",
                "estimated_time": "10-15 minutes",
                "complexity": "High"
            },
            {
                "name": "🌐 Web Scraper",
                "description": "Robust web scraping utility",
                "goal": "Build a web scraper with error handling, rate limiting, and data export capabilities",
                "estimated_time": "6-9 minutes",
                "complexity": "Medium"
            }
        ]

        for template in templates:
            with st.container():
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f"### {template['name']}")
                    st.caption(f"⏱️ {template['estimated_time']}")
                    st.caption(f"📊 {template['complexity']}")
                with col2:
                    st.markdown(template['description'])
                    st.markdown(f"**Goal:** {template['goal']}")

                    if st.button(f"Use This Template", key=f"template_{template['name']}"):
                        st.session_state.preset_goal = template['goal']
                        st.rerun()

                st.divider()

    def render_settings_page(self):
        """Render the settings page."""
        st.markdown("<div class='main-header'>⚙️ Settings</div>", unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["System", "API", "Dashboard"])

        with tab1:
            self._render_system_settings()

        with tab2:
            self._render_api_settings()

        with tab3:
            self._render_dashboard_settings()

    def _render_system_settings(self):
        """Render system settings."""
        st.markdown("**System Configuration**")

        col1, col2 = st.columns(2)

        with col1:
            # LLM Settings
            st.markdown("**🤖 LLM Configuration**")
            llm_provider = st.selectbox(
                "Default LLM Provider",
                ["OpenAI", "Anthropic", "Local (Ollama)", "Azure OpenAI"],
                index=0
            )

            api_key = st.text_input("API Key", type="password")

            max_tokens = st.slider("Max Tokens per Request", 100, 16000, 4000)
            temperature = st.slider("Temperature", 0.0, 2.0, 0.1, 0.1)

        with col2:
            # Pipeline Settings
            st.markdown("**⚙️ Pipeline Configuration**")

            default_timeout = st.number_input("Default Timeout (seconds)", 30, 3600, 300)
            max_concurrent = st.number_input("Max Concurrent Pipelines", 1, 100, 5)

            enable_self_healing = st.checkbox("Enable Self-Healing", True)
            require_human_approval = st.checkbox("Require Human Approval for Critical Actions", True)

        # Save settings
        if st.button("💾 Save System Settings", use_container_width=True):
            st.success("Settings saved successfully!")

    def _render_api_settings(self):
        """Render API settings."""
        st.markdown("**🔌 API Configuration**")

        # API Server
        api_host = st.text_input("API Host", "0.0.0.0")
        api_port = st.number_input("API Port", 1024, 65535, 8000)

        # Authentication
        st.markdown("**🔐 Authentication**")
        enable_auth = st.checkbox("Enable API Authentication", True)

        if enable_auth:
            auth_method = st.selectbox(
                "Authentication Method",
                ["API Key", "JWT", "OAuth2"],
                index=0
            )

            if auth_method == "API Key":
                api_keys = st.text_area(
                    "Valid API Keys (one per line)",
                    value="hive_dev_123\nhive_prod_456"
                )

        # Rate Limiting
        st.markdown("**⏱️ Rate Limiting**")
        enable_rate_limit = st.checkbox("Enable Rate Limiting", True)

        if enable_rate_limit:
            col1, col2 = st.columns(2)
            with col1:
                requests_per_minute = st.number_input("Requests per Minute", 1, 1000, 60)
            with col2:
                burst_limit = st.number_input("Burst Limit", 1, 100, 10)

        if st.button("💾 Save API Settings", use_container_width=True):
            st.success("API settings saved!")

    def _render_dashboard_settings(self):
        """Render dashboard settings."""
        st.markdown("**📊 Dashboard Configuration**")

        # Display Settings
        theme = st.selectbox("Theme", ["Light", "Dark", "Auto"], index=2)
        refresh_interval = st.selectbox(
            "Auto-refresh Interval",
            ["Off", "5 seconds", "15 seconds", "30 seconds", "1 minute"],
            index=2
        )

        # Data Retention
        st.markdown("**🗑️ Data Retention**")
        retain_sessions_days = st.slider("Retain Sessions (days)", 1, 365, 30)
        retain_metrics_days = st.slider("Retain Metrics (days)", 1, 365, 90)

        # Export Options
        st.markdown("**📤 Export Options**")
        enable_export = st.checkbox("Enable Data Export", True)

        if enable_export:
            export_formats = st.multiselect(
                "Export Formats",
                ["JSON", "CSV", "PDF", "HTML"],
                default=["JSON", "CSV"]
            )

        # Notifications
        st.markdown("**🔔 Notifications**")
        enable_notifications = st.checkbox("Enable Notifications", False)

        if enable_notifications:
            notification_method = st.multiselect(
                "Notification Methods",
                ["Email", "Slack", "Webhook", "In-app"],
                default=["In-app"]
            )

        if st.button("💾 Save Dashboard Settings", use_container_width=True):
            st.success("Dashboard settings saved!")

    def run(self):
        """Run the dashboard application."""
        # Initialize session state
        if "selected_session" not in st.session_state:
            st.session_state.selected_session = None
        if "replay_session" not in st.session_state:
            st.session_state.replay_session = None
        if "current_run" not in st.session_state:
            st.session_state.current_run = None

        # Render sidebar and get current page
        page = self.render_sidebar()

        # Render the selected page
        if page == "🏠 Dashboard":
            self.render_dashboard()
        elif page == "📊 Metrics":
            self.render_metrics_page()
        elif page == "🔍 Session Explorer":
            self.render_session_explorer()
        elif page == "🚀 Pipeline Runner":
            self.render_pipeline_runner()
        elif page == "⚙️ Settings":
            self.render_settings_page()


def main():
    """Main entry point for the dashboard."""
    dashboard = HiveDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()