source /etc/profile.d/conda.sh
conda activate client
cd server/life-agent
python -m streamlit run gpu_server/llm_webui_streamlit_server_phind.py --server.port 7860
