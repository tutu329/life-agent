source /etc/profile.d/conda.sh
conda activate client
cd server/life-agent
python -m gpu_server.llm_webui_server
