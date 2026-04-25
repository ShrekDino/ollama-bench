import streamlit as st
import requests
import time
import psutil
import pandas as pd
import threading
import GPUtil
import plotly.graph_objects as go

# --- CONFIG & STATE ---
OLLAMA_GEN_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

st.set_page_config(page_title="Olla-Metrics Pro", layout="wide")
st.title("💻 Olla-Metrics Dashboard") # Removed rocket emoji

if 'benchmark_data' not in st.session_state:
    st.session_state.benchmark_data = []

# --- HELPERS ---
def get_local_models():
    try:
        resp = requests.get(OLLAMA_TAGS_URL).json()
        return [m['name'] for m in resp['models']]
    except:
        return ["olmo-3:7b-think", "phi3", "llama3"]

def run_single_benchmark(model):
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
        # Timeout increased to 300s to prevent 'Read timed out' during model loading
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
        stop_event.set()
        if t.is_alive(): t.join()
        st.error(f"Failed {model}: {e}")
        return None

# --- SIDEBAR UI ---
st.sidebar.header("Benchmark Settings")
available_models = get_local_models()
selected_models = st.sidebar.multiselect("Select Models to Test", available_models, default=available_models[:3] if len(available_models) >=3 else available_models)

if st.sidebar.button("⚡ Start Benchmark"):
    st.session_state.benchmark_data = []
    chart_placeholder = st.empty()
    
    for model in selected_models:
        with st.status(f"Benchmarking {model}...", expanded=True) as status:
            # Short delay to allow VRAM to clear from previous model
            time.sleep(2) 
            result = run_single_benchmark(model)
            
            if result:
                st.session_state.benchmark_data.append(result)
                df = pd.DataFrame(st.session_state.benchmark_data)
                
                # --- ANIMATED PLOTLY SCATTER ---
                fig = go.Figure()
                metrics = ['TPS', 'GPU %', 'VRAM %', 'RAM %']
                colors = ['#00CC96', '#EF553B', '#636EFA', '#AB63FA']
                
                for idx, m in enumerate(metrics):
                    fig.add_trace(go.Scatter(
                        x=df['Model'], 
                        y=df[m], 
                        mode='markers+text',
                        name=m,
                        text=df[m],
                        textposition="top center",
                        marker=dict(
                            size=18, 
                            color=colors[idx],
                            line=dict(width=2, color='white')
                        )
                    ))

                fig.update_layout(
                    height=600,
                    title="Live Resource Telemetry",
                    yaxis=dict(title="Value", range=[0, 110]),
                    xaxis_title="Models",
                    template="plotly_dark",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    transition={'duration': 1200, 'easing': 'elastic-out'} 
                )
                chart_placeholder.plotly_chart(fig, use_container_width=True)
            status.update(label=f"Completed {model}!", state="complete", expanded=False)

# --- RESULTS TABLE ---
if st.session_state.benchmark_data:
    st.subheader("Benchmark Summary Table")
    st.dataframe(pd.DataFrame(st.session_state.benchmark_data), use_container_width=True)