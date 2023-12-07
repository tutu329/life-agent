rem set model_path=D:\models\Qwen-14B-Chat-GPTQ
rem set model_path=D:\models\XuanYuan-70B-Chat-4bit
rem set model_path=D:\models\openbuddy-llama2-70B-v13.2-GPTQ
rem set model_path=D:\models\Xwin-LM-70B-V0.1-GPTQ
set model_path=D:\models\Qwen-72B-Chat-Int4

rem set model_type=llama
set model_type=qwen

cmd /K "conda activate qwen && set CUDA_VISIBLE_DEVICES=0,1,3 && d: && cd d:\server\life-agent && start python -m gpu_server.qwen_client_webui && conda activate exllama && python -m gpu_server.openai_api_server --checkpoint-path=%model_path% --model-type=%model_type%"

