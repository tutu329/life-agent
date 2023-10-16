d:
cd d:\server\life-agent
cmd /K "conda activate qwen && set CUDA_VISIBLE_DEVICES=0,1 && python gpu_server\api_server_llm.py --model=wizard70"
