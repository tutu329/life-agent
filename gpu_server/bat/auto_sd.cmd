d:
cd D:\stable-diffusion-webui
cmd /K "set CUDA_VISIBLE_DEVICES=0 && set SD_WEBUI_RESTART='True' && D:\stable-diffusion-webui\venv\Scripts\activate.bat && python webui.py --opt-sdp-attention --api --server 0.0.0.0 --port 5000 --enable-insecure-extension-access --ad-no-huggingface --api-server-stop && C:\Users\tutu\Desktop\auto_sd.cmd"
