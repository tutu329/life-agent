source /etc/profile.d/conda.sh
conda activate client
cd /home/tutu/server/life-agent
python -m streamlit run gpu_server/llm_webui_streamlit_server.py --server.port 7861
