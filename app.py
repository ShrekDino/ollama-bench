import streamlit as st
import requests
import time
import psutil
import pandas as pd
import threading
import GPUtil
import plotly.graph_objects as go

# --- 1. CONFIGURATION & STATE ---
OLLAMA_GEN_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

def initialize_session():
    """Initializes global state variables without finicky run_ids."""
    if 'benchmark_data' not in st.session_state:
        st.session_state.benchmark_data = []

# --- 2. CORE LOGIC (Ollama & Resources) ---
def get_local_models():
    """Fetches list of models from local Ollama instance."""
    try:
        resp = requests.get(OLLAMA_TAGS_URL).json()
        return [m['name'] for m in resp['models']]
    except:
        return ["olmo-3:7b-think", "phi3", "llama3"]

def run_single_benchmark(model):
    """Handles model execution and peak resource tracking."""
    resource_stats = {'peak_cpu': 0, 'peak_gpu': 0, 'peak_vram': 0, 'peak_ram': 0}
    stop_event = threading.Event()

    def monitor():
        while not stop_event.is_set():
            resource_stats['peak_cpu'] = max(resource_stats['peak_cpu'], psutil.cpu_percent())
            resource_stats['peak_ram'] = max(resource_stats['peak_ram'], psutil.virtual_memory().percent)
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    resource_stats['peak_gpu'] = max(resource_stats['peak_gpu'], gpus[0].load * 100)
                    resource_stats['peak_vram'] = max(resource_stats['peak_vram'], gpus[0].memoryUtil * 100)
            except: pass
            time.sleep(0.1)

    t = threading.Thread(target=monitor)
    t.start()
    
    try:
        resp = requests.post(OLLAMA_GEN_URL, json={
            "model": model, 
            "prompt": "Explain the concept of entropy in three sentences.", 
            "stream": False
        }, timeout=300).json()
        
        stop_event.set()
        t.join()
        
        eval_dur = resp.get('eval_duration', 0) / 1e9
        tps = resp.get('eval_count', 0) / eval_dur if eval_dur > 0 else 0
        
        return {
            "Model": model,
            "TPS": round(tps, 2),
            "CPU %": round(resource_stats['peak_cpu'], 1),
            "GPU %": round(resource_stats['peak_gpu'], 1),
            "VRAM %": round(resource_stats['peak_vram'], 1),
            "RAM %": round(resource_stats['peak_ram'], 1)
        }
    except Exception as e:
        stop_event.set(); t.join()
        st.error(f"Failed {model}: {e}")
        return None

# --- 3. VISUALIZATION COMPONENTS ---
def render_metrics_chart(df):
    """Clean, non-animated scatter plot for comparative analysis."""
    fig = go.Figure()
    metrics = ['TPS', 'CPU %', 'GPU %', 'VRAM %', 'RAM %']
    colors = ['#00CC96', '#FFA15A', '#EF553B', '#636EFA', '#AB63FA']
    
    for idx, m in enumerate(metrics):
        fig.add_trace(go.Scatter(
            x=df['Model'], 
            y=df[m], 
            mode='markers+text',
            name=m,
            text=df[m],
            textposition="top center",
            marker=dict(size=14, color=colors[idx], line=dict(width=1, color='white'))
        ))

    fig.update_layout(
        height=500,
        margin=dict(l=20, r=20, t=40, b=20),
        yaxis=dict(title="Value / Percentage", range=[0, 120]),
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    return fig

def render_stat_cards(last_result):
    """Displays the most recent benchmark result in a sleek card row."""
    if not last_result: return
    
    cols = st.columns(5)
    metrics = [("TPS", "TPS"), ("CPU %", "CPU %"), ("GPU %", "GPU %"), ("VRAM %", "VRAM %"), ("RAM %", "RAM %")]
    
    for col, (label, key) in zip(cols, metrics):
        col.metric(label, f"{last_result[key]}")

# --- 4. UI SECTIONS ---
def sidebar_section():
    st.sidebar.header("⚙️ Settings")
    models = get_local_models()
    selected = st.sidebar.multiselect("Models", models, default=models[:3] if len(models) >= 3 else models)
    start_btn = st.sidebar.button("⚡ Run Benchmark")
    if st.sidebar.button("🗑️ Clear Results"):
        st.session_state.benchmark_data = []
        st.rerun()
    return start_btn, selected

# --- 5. MAIN EXECUTION ---
def main():
    st.set_page_config(page_title="Olla-Metrics Pro", layout="wide")
    st.markdown("### 📊 Local LLM Performance Benchmarking")
    initialize_session()

    start_btn, selected_models = sidebar_section()

    # Placeholders for dynamic UI
    card_container = st.container()
    chart_placeholder = st.empty()

    if start_btn:
        st.session_state.benchmark_data = []
        
        for model in selected_models:
            with st.status(f"Testing {model}...", expanded=False) as status:
                result = run_single_benchmark(model)
                
                if result:
                    st.session_state.benchmark_data.append(result)
                    
                    # Update Stat Cards for immediate impact
                    with card_container:
                        st.write(f"**Latest Result: {model}**")
                        render_stat_cards(result)
                    
                    # Update Chart (No keys, no animation, no errors)
                    df = pd.DataFrame(st.session_state.benchmark_data)
                    chart_placeholder.plotly_chart(render_metrics_chart(df), use_container_width=True)
                
                status.update(label=f"Done: {model}", state="complete")

    # Final summary table
    if st.session_state.benchmark_data:
        st.divider()
        st.subheader("📋 Full Result Set")
        st.dataframe(pd.DataFrame(st.session_state.benchmark_data), use_container_width=True)

if __name__ == "__main__":
    main()