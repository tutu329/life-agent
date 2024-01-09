export CUDA_VISIBLE_DEVICES=0,1,3,2
python -m vllm.entrypoints.openai.api_server --model=/home/tutu/models/Qwen-72B-Chat-Int4 --tensor-parallel-size=4 --trust-remote-code --chat-template=/home/tutu/models/template_chatml.jinja --host=0.0.0.0 --port=8001
