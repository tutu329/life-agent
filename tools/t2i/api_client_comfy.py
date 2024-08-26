#This is an example that uses the websockets api and the SaveImageWebsocket node to get images directly without
#them being saved to disk

import websocket #NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import uuid
import json
import urllib.request
import urllib.parse
import random

from PIL import Image
import io
# from IPython.display import display

from dataclasses import dataclass, field
from colorama import Fore, Back, Style

import config


@dataclass
class Work_Flow_Type():
    simple:int = 1

class Work_Flow_Template():
    template = {
        Work_Flow_Type.simple : """
{
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "cfg": 1,
            "denoise": 1,
            "latent_image": [
                "5",
                0
            ],
            "model": [
                "4",
                0
            ],
            "negative": [
                "7",
                0
            ],
            "positive": [
                "6",
                0
            ],
            "sampler_name": "euler",
            "scheduler": "sgm_uniform",
            "seed": 689141365006356,
            "steps": 2
        }
    },
    "4": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": "sdxl_lightning_2step.safetensors"
        }
    },
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "batch_size": 1,
            "height": 1024,
            "width": 1024
        }
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": [
                "4",
                1
            ],
            "text": "masterpiece best quality girl"
        }
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": [
                "4",
                1
            ],
            "text": "bad hands"
        }
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": [
                "3",
                0
            ],
            "vae": [
                "4",
                2
            ]
        }
    },
    "save_image_websocket_node": {
        "class_type": "SaveImageWebsocket",
        "inputs": {
            "images": [
                "8",
                0
            ]
        }
    }
}
""",
    }

from config import Port, Global
class Comfy:
    def __init__(self):
        self.server_address = config.Domain.comfyui_server_domain
        self.client_id = None
        self.images = None
        self.temp_dir = Global.temp_dir

        self.workflow_type = Work_Flow_Type.simple

        self.prompt = None

    def set_workflow_type(self, type:Work_Flow_Type):
        self.workflow_type = type

    def set_sd3_workflow(
            self,
            positive='photo of young man in an grayed blue suit, light green shirt, and yellow tie. He has a neatly styled haircut with red and silver hair and is looking directly at the camera with a neutral expression. The background is seaside. The photograph is in colored, emphasizing contrasts and shadows. The man appears to be in his late twenties or early thirties, with fair skin and short.This man looks very like young Tom Cruise.',
            negative='ugly face, bad hands, bad fingers, bad quality, poor quality, doll, disfigured, jpg, toy, bad anatomy, missing limbs, missing fingers, 3d, cgi',
            template_json_file='api-sd3-tom.json',
            seed=random.randint(1, 1e14),
            ckpt_name='sd3_medium.safetensors',
            height=1024,
            width=1024,
            sampler_name='dpmpp_2m',
            scheduler='sgm_uniform',
            steps=30,
            cfg=4.5,
            denoise=1,
            batch_size=1,
    ):
        print(f'------------------template_json_file: {template_json_file}------------------')
        with open(template_json_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
        print(f'------------------data------------------')
        for k,v in data.items():
            print(f'\t {k}: {v}')

        self.prompt = data

        self.prompt['6']['inputs']['text'] = positive
        self.prompt['71']['inputs']['text'] = negative
        self.prompt['252']['inputs']['ckpt_name'] = ckpt_name
        self.prompt['135']['inputs']['height'] = height
        self.prompt['135']['inputs']['width'] = width
        self.prompt['135']['inputs']['batch_size'] = batch_size
        self.prompt['271']['inputs']['sampler_name'] = sampler_name
        self.prompt['271']['inputs']['scheduler'] = scheduler
        self.prompt['271']['inputs']['cfg'] = cfg
        self.prompt['271']['inputs']['denoise'] = denoise
        self.prompt['271']['inputs']['steps'] = steps
        self.prompt['271']['inputs']['seed'] = seed

    def set_sexy_workflow(
            self,
            using_template=1,    # 用于redis_proxy_server中
            positive='masterpiece,best quality,absurdres,highres,4k,ray tracing,perfect face,perfect eyes,intricate details,highly detailed, 1girl,(breasts:1.2),moyou,looking at viewer,sexy pose,(cowboy shot:1.2), <lora:Tassels Dudou:0.8>,Tassels Dudou,white dress,back,',
            negative='EasyNegativeV2,(badhandv4:1.2),bad-picture-chill-75v,BadDream,(UnrealisticDream:1.2),bad_prompt_v2,NegfeetV2,ng_deepnegative_v1_75t,ugly,(worst quality:2),(low quality:2),(normal quality:2),lowres,watermark,',
            template_json_file='api-sexy.json',
            seed=random.randint(1, 1e14),
            ckpt_name='meichidarkMix_meichidarkV5.safetensors',
            height=768,
            width=512,
            sampler_name='dpmpp_2m_sde',
            scheduler='karras',
            steps=72,
            cfg=7,
            denoise=1,
            batch_size=1,
            lora_count=1,
            lora1='None',
            # lora1='sexy-cloth-Tassels-Dudou.safetensors',
            lora1_wt=1,
            # lora1_wt=0.85,
            lora2='None',
            lora2_wt=1,
            lora3='None',
            lora3_wt=1,
            lora4='None',
            lora4_wt=1,
    ):
        with open(template_json_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
        print(f'------------------json data------------------')
        for k,v in data.items():
            print(f'\t {k}: {v}')

        self.prompt = data


        print(f'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@set_sexy_workflow(), positive:{positive}@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
        self.prompt['13']['inputs']['positive'] = positive
        self.prompt['13']['inputs']['negative'] = negative
        self.prompt['13']['inputs']['ckpt_name'] = ckpt_name
        self.prompt['13']['inputs']['empty_latent_height'] = height
        self.prompt['13']['inputs']['empty_latent_width'] = width
        self.prompt['13']['inputs']['batch_size'] = batch_size

        # 绘图参数
        self.prompt['16']['inputs']['sampler_name'] = sampler_name
        self.prompt['16']['inputs']['scheduler'] = scheduler
        self.prompt['16']['inputs']['cfg'] = cfg
        self.prompt['16']['inputs']['denoise'] = denoise
        self.prompt['16']['inputs']['steps'] = steps
        self.prompt['16']['inputs']['seed'] = seed

        # 面部修复参数
        self.prompt['20']['inputs']['sampler_name'] = sampler_name
        self.prompt['20']['inputs']['scheduler'] = scheduler
        self.prompt['20']['inputs']['cfg'] = 2
        self.prompt['20']['inputs']['denoise'] = denoise
        self.prompt['20']['inputs']['steps'] = 10
        self.prompt['20']['inputs']['seed'] = seed

        # Lora-Stacker
        self.prompt['12']['inputs']['lora_count'] = lora_count
        self.prompt['12']['inputs']['lora_name_1'] = lora1
        self.prompt['12']['inputs']['lora_wt_1'] = lora1_wt
        self.prompt['12']['inputs']['lora_name_2'] = lora2
        self.prompt['12']['inputs']['lora_wt_2'] = lora2_wt
        self.prompt['12']['inputs']['lora_name_3'] = lora3
        self.prompt['12']['inputs']['lora_wt_3'] = lora3_wt
        self.prompt['12']['inputs']['lora_name_4'] = lora4
        self.prompt['12']['inputs']['lora_wt_4'] = lora4_wt

    def set_workflow_by_json_file(self, in_json_file):
        with open(in_json_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
            # print(data)
        self.prompt = data
        # seed = random.randint(1, 1e14)
        # print(f'seed: "{seed}"')
        self._update_seed_in_json()
        # self.prompt[seed_node]['inputs']['seed'] = seed

    def _update_seed_in_json(self):
        # 注意positive和修脸等节点的seed要一致
        random_seed = random.randint(1, 1e14)
        for k,v in self.prompt.items():
            node = k
            node_dict = v
            if 'inputs' in node_dict:
                for k1,v1 in self.prompt[node]['inputs'].items():
                    inputs_key = k1
                    if inputs_key=='seed':
                        # 更新seed随机数
                        self.prompt[node]['inputs']['seed'] = random_seed

    def is_image_websocket_node(self, in_node):
        return self.prompt[str(in_node)]["class_type"] == "SaveImageWebsocket"

    def set_simple_work_flow(
            self,
            positive,
            negative='',
            seed=random.randint(1, 1e14),
            ckpt_name='sdxl_lightning_2step.safetensors',
            height=1024,
            width=1024,
            sampler_name='euler',
            scheduler='sgm_uniform',
            steps=2,
            cfg=1,
            denoise=1,
            batch_size=1,
    ):
        print(f'seed: "{seed}"')
        # 设置simple工作流模板
        self.prompt = json.loads(Work_Flow_Template.template[self.workflow_type])

        # 设置simple工作流参数
        self.prompt['3']['inputs']['seed'] = seed

        self.prompt['3']['inputs']['sampler_name'] = sampler_name
        self.prompt['3']['inputs']['scheduler'] = scheduler
        self.prompt['3']['inputs']['steps'] = steps
        self.prompt['3']['inputs']['cfg'] = cfg
        self.prompt['3']['inputs']['denoise'] = denoise

        self.prompt['4']['inputs']['ckpt_name'] = ckpt_name

        self.prompt['5']['inputs']['height'] = height
        self.prompt['5']['inputs']['width'] = width
        self.prompt['5']['inputs']['batch_size'] = batch_size

        self.prompt['6']['inputs']['text'] = positive   # 如: "masterpiece best quality girl"
        self.prompt['7']['inputs']['text'] = negative   # 如: "bad hands"


    def get_images(self):
        self.client_id = str(uuid.uuid4())

        ws = websocket.WebSocket()
        ws.connect("ws://{}/ws?clientId={}".format(self.server_address, self.client_id))

        # print(f'get_images(): self.prompt="{self.prompt}"')
        images = self._get_images(ws, self.prompt, self.client_id)
        # print(f'get_images(): images="{images}"')

        self.images = images
        return images

    def set_server_address(self, address=config.Domain.comfyui_server_domain):
        self.server_address = address

    def set_temp_dir(self, dir=Global.temp_dir):
        self.temp_dir = dir

    def get_temp_dir(self):
        return self.temp_dir

    def save_images_to_temp_dir(self):
        i=0
        for node_id in self.images:
            for image_data in self.images[node_id]:
                from PIL import Image
                import io
                image = Image.open(io.BytesIO(image_data))
                image.save(f'{self.temp_dir}/{self.client_id}_{i}.jpg')
                i += 1

    def _get_images(self, ws, prompt, client_id):
        prompt_id = self._queue_prompt(prompt, client_id)['prompt_id']
        output_images = {}
        current_node = ""
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                print(f'message: "{message}"')
                if message['type'] == 'executing':
                    data = message['data']
                    if data['prompt_id'] == prompt_id:
                        if data['node'] is None:
                            print('数据均已返回.')
                            break  # Execution is done
                        else:
                            current_node = data['node']
                            print(f'处理节点【{current_node}】...')

            else:
                if self.is_image_websocket_node(current_node):
                # if current_node == 'save_image_websocket_node':
                    print('节点【save_image_websocket_node】输出数据...')
                    images_output = output_images.get(current_node, [])
                    images_output.append(out[8:])
                    output_images[current_node] = images_output

        return output_images

    def _get_image(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen("http://{}/view?{}".format(self.server_address, url_values)) as response:
            return response.read()

    def _get_history(self, prompt_id):
        with urllib.request.urlopen("http://{}/history/{}".format(self.server_address, prompt_id)) as response:
            return json.loads(response.read())

    def _queue_prompt(self, prompt, client_id):
        p = {"prompt": prompt, "client_id": client_id}
        data = json.dumps(p).encode('utf-8')
        req =  urllib.request.Request("http://{}/prompt".format(self.server_address), data=data)
        return json.loads(urllib.request.urlopen(req).read())

def main():
    client = Comfy()
    client.set_server_address('localhost:5100')
    # client.set_server_address('192.168.124.33:7869')

    # client.set_workflow_type(Work_Flow_Type.simple)
    # t = 0
    # if t==1:
    #     client.set_simple_work_flow(
    #         positive='super man',
    #         # negative='ugly',
    #         # seed=seed,
    #         ckpt_name='sdxl_lightning_2step.safetensors',
    #         height=512,
    #         width=512,
    #     )
    # else:
    #     # client.set_workflow_by_json_file('api-sd3-tom.json', seed_node='271')
    #     client.set_workflow_by_json_file('api-sexy-back-liusu.json')
    #     # client.set_workflow_by_json_file('api3.json')

    import glob,os
    path = 'D:\\server\\life-agent\\redis_proxy\\custom_command\\t2i\\api'
    json_files = glob.glob(os.path.join(path, '*.json'))
    print(json_files)
    for i in range(10):
        template_json_file = random.choice(json_files)
        print(template_json_file)
        client.set_workflow_by_json_file(template_json_file)

        client.get_images()
        client.save_images_to_temp_dir()




if __name__ == "__main__" :
    main()
