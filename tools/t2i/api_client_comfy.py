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
        self.server_address = f'127.0.0.1:{Port.comfy}' # 127.0.0.1:7869
        self.client_id = None
        self.images = None
        self.temp_dir = Global.temp_dir

        self.workflow_type = Work_Flow_Type.simple

        self.prompt = None

    def set_workflow_type(self, type:Work_Flow_Type):
        self.workflow_type = type

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
    ):
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

        self.prompt['6']['inputs']['text'] = positive   # 如: "masterpiece best quality girl"
        self.prompt['7']['inputs']['text'] = negative   # 如: "bad hands"


    def get_images(self):
        self.client_id = str(uuid.uuid4())

        ws = websocket.WebSocket()
        ws.connect("ws://{}/ws?clientId={}".format(self.server_address, self.client_id))

        images = self._get_images(ws, self.prompt, self.client_id)

        self.images = images

    def set_server_address(self, address=f'127.0.0.1:{Port.comfy}'):
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
                if message['type'] == 'executing':
                    data = message['data']
                    if data['prompt_id'] == prompt_id:
                        if data['node'] is None:
                            break  # Execution is done
                        else:
                            current_node = data['node']
            else:
                if current_node == 'save_image_websocket_node':
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
    client.set_server_address('192.168.124.33:7869')
    client.set_workflow_type(Work_Flow_Type.simple)
    client.set_simple_work_flow(
        positive='super man',
        negative='ugly',
        # seed=seed,
        ckpt_name='sdxl_lightning_2step.safetensors',
        height=1024,
        width=1024,
    )
    client.get_images()
    client.save_images_to_temp_dir()

if __name__ == "__main__" :
    main()
