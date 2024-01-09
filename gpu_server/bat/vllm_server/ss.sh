source /etc/profile.d/conda.sh
./start_frpc.sh
conda activate v
nohup ./ju.sh &
nohup ./vllm_server.sh &
sleep 146
nohup ./streamlit_client.sh & 

