d:
cd D:\stable-diffusion-webui
cmd /K "set CUDA_VISIBLE_DEVICES=0 && D:\stable-diffusion-webui\venv\Scripts\activate.bat && python webui.py --xformers --api --server 0.0.0.0 --port 5000 --enable-insecure-extension-access --ad-no-huggingface --api-server-stop"

