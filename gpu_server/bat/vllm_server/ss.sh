source /etc/profile.d/conda.sh
/home/tutu/start_frpc.sh
conda activate v
nohup /home/tutu/ju.sh &
nohup /home/tutu/vllm_server.sh &
sleep 146
nohup /home/tutu/streamlit_client.sh & 

