set model_path=D:\models\Qwen-72B-Chat-Int4
set model_type=qwen
cmd /K "conda activate qwen && set CUDA_VISIBLE_DEVICES=0,1,3,2 && d: && cd d:\server\life-agent && start python -m gpu_server.qwen_client_webui && python -m gpu_server.openai_api_server --checkpoint-path=%model_path% --model-type=%model_type%"

