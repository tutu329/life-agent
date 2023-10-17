import json
import requests
import io, os
import base64
from PIL import Image, PngImagePlugin, GifImagePlugin
from copy import deepcopy
import uuid

class Stable_Diffusion():
    _negative_prompt_list = [
        '(worst quality:2),(low quality:2),(normal quality:2),lowres,watermark,badhandv4,ng_deepnegative_v1_75t',
        # "ugly face",
        # "ugly eyes",
        # "ugly nose",
        # "mutated hands and fingers",  # 变异的手和手指
        # "deformed",  # 畸形的
        # "bad anatomy",  # 解剖不良
        # "disfigured",  # 毁容
        # "poorly drawn face",  # 脸部画得不好
        # "mutated",  # 变异的
        # "extra limb",  # 多余的肢体
        # "ugly",  # 丑陋
        # "poorly drawn hands",  # 手部画的很差
        # "missing limb",  # 缺少肢体
        # "floating limbs",  # 漂浮的四肢
        # "disconnected limbs",  # 肢体不连贯
        # "malformed hands",  # 畸形手
        # "out of focus",  # 脱离焦点
        # "(((naked)))",
        # "(((nude)))",
        # "(((pussy)))",
        # "(((vagina)))",
        # "(((penis)))",
    ]

    _prefix_quality = [  # 前缀画质
        'masterpiece',  # 杰作
        'extremely detailed wallpaper',
        'incredibly absurdres',
        '8k',
        'best quality',
    ]

    _subject_gesture = {  # 姿势
        '膝到胸': 'knees to chest',  # 膝到胸
        '双膝并拢脚分开': 'knees together feet apart',  # 双膝并拢脚分开
        '双腿分开': 'legs apart',  # 双腿分开
        '手夹腿间': 'hand between legs',  # 手夹腿间
        'M字腿': 'm legs',  # M字腿
        '蹲下': 'squatting',  # 蹲下
        '走': 'walking',  # 走
        '自拍': 'selfie',  # 自拍
        '张腿': 'spread_legs',  # 张腿
        '站立': 'standing',  # 站立
        '向后看': 'looking_back',  # 向后看
        '躺着': 'lying on back',  # 躺着
        '睡觉': 'sleeping',  # 睡觉
        '翘臀': 'bent_over',  # 翘臀
        '趴着翘臀': 'top-down_bottom-up',  # 趴着翘臀
        '单手叉腰': 'hand_on_hip',  # 单手叉腰
        '搓头发': 'hair scrunchie',  # 搓头发
        '侧卧': 'on side',  # 侧卧
        '侧身坐': 'yokozuwari',  # 侧身坐
    }

    _subject_clothing = {  # 服装
        # 上装
        '透视连衣裙': 'see-through dress',  # 透视连衣裙      非常好看
        '正装衬衫': 'dress shirt',  # 正装衬衫
        '露脐上衣': 'crop top',  # 露脐上衣
        '披风': 'capelet',  # 披风
        '露腰上衣': 'midriff',  # 露腰上衣
        '卫衣': 'hoodie',  # 卫衣
        '夹克': 'jacket',  # 夹克
        '束身胸衣': 'corset',  # 束身胸衣
        '心形镂空': 'clothing heart shaped cutout',  # 心形镂空
        '罩衫': 'blouse',  # 罩衫
        '运动衫': 'jersey',  # 运动衫
        '燕尾服': 'tailcoat',  # 燕尾服
        '袖肩分离装': 'detached sleeves',  # 袖肩分离装
        '脱下比基尼上衣': 'bikini top removed',  # 脱下比基尼上衣
        '丝带': 'ribbon',  # 丝带
        '湿衬衫': 'wet shirt',  # 湿衬衫
        '上衣较少': 'topless',  # 上衣较少
        '裸体披风': 'naked cape',  # 裸体披风
        '裸体衬衫': 'naked shirt',  # 裸体衬衫
        '解开纽扣的衬衫': 'unbuttoned shirt',  # 解开纽扣的衬衫
        '肩部镂空': 'shoulder cutout',  # 肩部镂空
        '短衬衫': 'cropped shirt',  # 短衬衫
        '肚兜': 'dudou',  # 肚兜
        '低胸': 'lowleg',  # 低胸
        '处男杀手毛衣': 'virgin killer sweater',  # 处男杀手毛衣
        '比基尼上衣': 'bikini top',  # 比基尼上衣
        'T恤': 't-shirt',  # T恤
        '胸部开口的毛衣': 'open-chest sweater',  # 胸部开口的毛衣
        '小款背心': 'cropped vest',  # 小款背心
        '无袖紧身背心': 'tank top',  # 无袖紧身背心
        '露肩毛衣': 'off-shoulder sweater',  # 露肩毛衣
        '长袖': 'long sleeves',  # 长袖

        '透明装':'see-through',
        '脱下衣物':'clothes down',
        '蕾丝':'organza lace',
        '浴衣':'yukata',
        '情趣内衣':'sex underwear',
        '裸体丝带':'naked ribbonr',
        '裸体围裙':'apron on naked body',

        # 下装
        '迷你裙': 'miniskirt',  # 迷你裙
        '超短裙': 'microskirt',  # 超短裙         非常好看
        '包臀裙': 'sheath dress',  # 包臀裙
        '露背吊带裙': 'halter dress',  # 露背吊带裙
        '紧身裙': 'Pencil Skirt',  # 紧身裙
        '几乎赤裸的围裙': 'nearly naked apron',  #
        '下衣较少': 'bottomless',  #

        '湿连裤袜': 'wet pantyhose',  #
        '撕裂连裤袜': 'torn bodystocking',  #
        '黑色连裤袜': 'black pantyhose',  #

        # 鞋子
        '高跟鞋': 'high heels',  # 高跟鞋
        '裸足凉鞋': 'barefoot sandals',  # 裸足凉鞋
    }

    _subject_underwear = {  # 内衣
        '胸罩': 'bra',  # 胸罩
        '普通内衣': 'underwear',  # 普通内衣
        '无胸罩': 'no bra',  # 无胸罩
        '无肩带文胸': 'strapless bra',  # 无肩带文胸
        '蕾丝胸罩': 'lace bra',  # 蕾丝胸罩
        '蕾丝边饰文胸': 'lace-trimmed bra',  # 蕾丝边饰文胸
        '乳房之间的带子': 'strap between breasts',  # 乳房之间的带子
        '成人内衣': 'lingerie',  # 成人内衣
        '摘下的胸罩': 'bra removed',  # 摘下的胸罩
        '覆盖少的吊带胸罩': 'strap gap',  # 覆盖少的吊带胸罩
        '带蝴蝶结的胸罩': 'bow bra',  # 带蝴蝶结的胸罩
    }

    _subject_panties = {  # 内裤
        '无内裤': 'no panties',  #
        '丁字裤': 'thong',  #
        '开档内裤': 'crotchless panties',  #
        '高开衩内裤': 'highleg panties',  #
        '超细丁字裤': 'g-string',  #
        '阴贴': 'maebari',  #
        '布料很少的内裤': 'micro panties',  #
    }

    _prefix_shot = {  # 前缀镜头效果
        # 平面角度
        '正面': 'front view',  # 正面
        '后面': 'back view',  # 后面
        '左侧': 'left side view',  # 左侧
        '右侧': 'right side view',  # 右侧
        '45度': '45-degree shot',  # 45度侧
        # 纵向角度
        '顶部': 'top shot',  # 顶部角度
        '高角度': 'high angle shot',  # 高角度
        '低角度': 'low angle shot',  # 低角度
        # 镜头高度
        '眼睛位置': 'eye level shot',  # 眼睛
        '肩膀位置': 'shoulder level shot',  # 肩膀
        '臀部位置': 'hip level shot',  # 臀部
        '膝盖位置': 'knee level shot',  # 膝盖
        '地面位置': 'ground level shot',  # 地面
        # 镜头景别
        '超全景': 'extreme long shot',  # 超全景
        # 'very long': 'very long shot',  # 超全景
        '全景': 'long shot',  # 全景
        '中远景': 'medium long shot',  # 中远景
        '中景特写': 'medium close up',  # 中景特写
        '特写': 'close up',  # 特写
        '大特写': 'extreme close up',  # 大特写

        # 人身拍摄位置
        '第一人称': 'pov',  # 第一人称
        '正面视角全身': 'full body',  # 正面视角全身
        '正面从头到腰': 'cowboy shot',  # 正面从头到腰
        '戏剧性角度': 'dramatic angle',  # 戏剧性角度
        '半身': 'bust',  # 半身
        '上半身': 'upper body',  # 上半身
        '下半身': 'lower body',  # 下半身
        '多视图': 'multiple views',  # 多视图
        '自拍镜': 'selfiemirror',  # 自拍镜
        '正脸': 'straight-on',  # 正脸
        '臀部焦点': 'ass focus',  # 臀部焦点
        '从裙底往上看': 'upskirt',  #
        '从短裤往上看': 'upshorts',  #
        '从衬衫往上看': 'upshirt',  #
        '两腿之间': 'between legs',  # 两腿之间
        '大腿之间': 'between thighs',  # 大腿之间
    }

    _prefix_style = {  # 前缀画风
        '照片': 'photo',  # 照片
        '优化': 'oil painting',  # 油画
        'CG': 'cg',  # CG
        '漫画': 'comic',  # 漫画
        '动漫': 'anime',  # 动漫
        '手绘': 'sketch',  # 手绘
        'Q版': 'chibi',  # Q版

        '现实': 'realistic',  # 现实
        '单色': 'monochrome',  # 单色
        '灰度': 'greyscale',  # 灰度
        '黑白少量颜色': 'spot color',  # 黑白画中的少量颜色
        '高对比度': 'high contrast',  # 高对比度
        '部分着色': 'partially colored',  # 部分着色

        '新艺术运动': 'art nouveau',  # 新艺术运动
        '杂志封面': 'magazine cover',  # 杂志封面
        '水彩': 'watercolor',  # 水彩
        '赛博朋克': 'cyberpunk',  # 赛博朋克
        '虚实穿插': 'fourth wall',  # 虚实穿插或现实感或次元壁
        '彩铅': 'watercolor pencil',  # 彩铅
        '仿手办': 'faux figurine',  # 仿手办风格
        '表情展示': 'expression chart',  # 角色的多表情展示
        '运动线': 'motion lines',  # 体现运动的线
    }

    _prefix_light = {  # 前缀光照效果
        '逆光': 'backlighting',  # 逆光
        '背景虚化': 'depth of field',  # 背景虚化
        '锐利焦点': 'sharp focus',  # 锐利的焦点
        '体积光': 'volume light',  # 体积光
        '电影光效': 'cinematic lighting',  # 电影光效
        '镜头光晕': 'lens flare',  # 镜头光晕
    }

    _scene_env = {  # 场景环境
        '山顶': 'the top of the hill',  # 山顶
        '海滩': 'on the beach',  # 海滩
        '夏威夷': 'in hawaii',  # 夏威夷
        '巴洛克建筑': 'in the baroque architecture',  # 巴洛克建筑
        '罗马街道': 'in the romanesque architecture streets',  # 罗马街道
        '街上': 'in the street',  # 街上
        '温泉': 'onsen',  # 温泉
        '酒吧': 'in a bar',  # 酒吧
        '教堂': 'church',  # 教堂
        '更衣室': 'in a locker room',  # 更衣室
        '星巴克': 'starbucks',  # 星巴克
        '舞台': 'stage',  # 舞台
        '森林': 'forest',  # 森林
        '漂亮的水': 'beautiful detailed water',  # 漂亮的水
        '教室': 'classroom',  # 教室
        '户外': 'outdoors',  # 户外
        '公园': 'park',  # 公园
        '餐厅': 'restaurant',  # 餐厅
        '商店': 'shop',  # 商店
        '摩天大楼': 'skyscrapers',  # 摩天大楼
        '废墟遗迹': 'ruins',  # 废墟遗迹
        '高原': 'plateau',  # 高原沙漠
        '城堡外': 'at the castle',  # 在城堡外
        '城堡里': 'in the castle',  # 在城堡内
    }

    def __init__(self, in_model="majicmixRealistic_betterV2V25.safetensors", in_url="http://localhost:5000"):
        self.model = in_model
        self.url = in_url

        # comma
        self.comma = ','

        # 本次绘画的参数
        self._draw_parameters = {}
        self._hires_draw_parameters = {}
        self.restore_face_by_adetailer = False

    def init(self):
        # 设置checkpoint模型
        sd_model = {
            "sd_model_checkpoint": self.model,
        }
        response = requests.post(url=f'{self.url}/sdapi/v1/options', json=sd_model)
        print(f'stable diffusion model: "{self.model}" ')

    def build_negative_prompt(self):
        negative_prompt = self.comma.join(Stable_Diffusion._negative_prompt_list)

        print(f'negative_prompt: "{negative_prompt}" ')
        return negative_prompt

    def build_prompt(self,
                     in_other='',
                     in_up_cloth='露背吊带裙',
                     in_bottom_cloth='迷你裙',
                     in_underwear='无胸罩',
                     in_panties='无内裤',
                     in_shoe='高跟鞋',
                     in_gesture='站立',
                     in_shot='大特写',
                     in_light='电影光效',
                     in_style1='照片',
                     in_style2='现实',
                     in_env='海滩',
                     in_role='asian girl',
                     in_expression='shy,smile',
                     in_hair='drill hair,long hair,shiny hair,hair strand,light brown hair',  # 公主卷、长发、有光泽、一缕一缕、浅褐色
                     in_eyes='blue eyes',
                     in_lip='red lip',
                     in_face='(perfect face)',
                     in_legs='(thin legs:1.3),(long legs:1.5),(super model),(slim waist)',
                     in_breast='small breasts',):
        prompt = ''
        prompt += in_other + self.comma

        prompt += self.comma.join(Stable_Diffusion._prefix_quality) + self.comma

        _subject_role = {  # 主体人物或对象
            'role': in_role,
            'expression': in_expression,
            'hair': in_hair,
            'eyes': in_eyes,
            'lip': in_lip,
            'face': in_face,
            'legs': in_legs,
            'breast': in_breast,
        }

        prompt += self.comma.join([
            _subject_role['role'],
            _subject_role['expression'],
            _subject_role['hair'],
            _subject_role['eyes'],
            _subject_role['lip'],
            _subject_role['face'],
            _subject_role['legs'],
            _subject_role['breast'],

            Stable_Diffusion._subject_gesture[in_gesture],          # 姿势

            Stable_Diffusion._prefix_shot[in_shot],                 # 镜头
            Stable_Diffusion._prefix_light[in_light],               # 光效

            Stable_Diffusion._subject_clothing[in_up_cloth],        # 上衣
            Stable_Diffusion._subject_clothing[in_bottom_cloth],    # 下衣
            Stable_Diffusion._subject_clothing[in_shoe],            # 鞋子
            Stable_Diffusion._subject_underwear[in_underwear],      # 内衣
            Stable_Diffusion._subject_panties[in_panties],      # 内裤

            Stable_Diffusion._scene_env[in_env],                    # 环境

            Stable_Diffusion._prefix_style[in_style1],              # 风格1
            Stable_Diffusion._prefix_style[in_style2],              # 风格2
        ]) + self.comma

        print(f'prompt: "{prompt}" ')
        return prompt

    def set_prompt(self, in_prompt, in_sampler, in_cfg_scale=7, in_restore_face_by_adetailer=True, in_negative_prompt="", in_hires_img=True, in_l_size=768, in_s_size=512, in_vertical=True, in_batch_size=1, in_steps=30):
        self.restore_face_by_adetailer = in_restore_face_by_adetailer
        self.hires_img = in_hires_img     # hires仅用于image，无法用于animatediff的video
        self._hires_draw_parameters = {
            "prompt": in_prompt,
            "negative_prompt": in_negative_prompt,
            # "prompt": "close up 1 chinese girl close-up of buttocks, pefect leg longleg 8k casual shirt  transparent no bra no trousers large middle b-cup pefect face ultra detail perfect butt perfect eyes ultra detail  full body  light and shadow",
            # "prompt": "close up 1 chinese girl (ground level shot:1.5) pefect leg longleg 8k casual shirt  transparent no bra no trousers large middle b-cup pefect face ultra detail perfect butt perfect eyes ultra detail  full body  light and shadow",
            "steps": 20,
            "restore_faces": True,
            "width": in_s_size if in_vertical else in_l_size,
            "height": in_l_size if in_vertical else in_s_size,
            "batch_size": in_batch_size,
            "sampler_index": in_sampler,
            "cfg_scale": in_cfg_scale,

            'enable_hr': True,
            "hr_scale": 2,
            "denoising_strength": 0.3,
            "hr_upscaler": 'R-ESRGAN 4x+',
            "hr_sampler": 'DPM++ 2M Karras',

            "seed": -1,
        }
        self._draw_parameters = {
            "prompt": in_prompt,
            "negative_prompt": in_negative_prompt,
            # "prompt": "close up 1 chinese girl close-up of buttocks, pefect leg longleg 8k casual shirt  transparent no bra no trousers large middle b-cup pefect face ultra detail perfect butt perfect eyes ultra detail  full body  light and shadow",
            # "prompt": "close up 1 chinese girl (ground level shot:1.5) pefect leg longleg 8k casual shirt  transparent no bra no trousers large middle b-cup pefect face ultra detail perfect butt perfect eyes ultra detail  full body  light and shadow",
            "steps": in_steps,
            "restore_faces": not in_restore_face_by_adetailer,
            "width": in_s_size if in_vertical else in_l_size,
            "height": in_l_size if in_vertical else in_s_size,
            "batch_size": in_batch_size,
            "sampler_index": in_sampler,
            "cfg_scale": in_cfg_scale,

            "seed": -1,
        }

        # webui的插件参数
        plugin_adetailer = {
            # 'other plugin':{
            #     'args':[]
            # },
            'ADetailer': {
                "args": [
                    in_restore_face_by_adetailer,
                    {
                        # "ad_model": "face_yolov8n.pt",
                        "ad_model": "mediapipe_face_full",
                        "ad_prompt": "",
                        "ad_negative_prompt": "",
                        "ad_confidence": 0.3,
                        "ad_mask_k_largest": 0,
                        "ad_mask_min_ratio": 0.0,
                        "ad_mask_max_ratio": 1.0,
                        "ad_dilate_erode": 32,
                        "ad_x_offset": 0,
                        "ad_y_offset": 0,
                        "ad_mask_merge_invert": "None",
                        "ad_mask_blur": 4,
                        "ad_denoising_strength": 0.4,
                        "ad_inpaint_only_masked": True,
                        "ad_inpaint_only_masked_padding": 0,
                        "ad_use_inpaint_width_height": False,
                        "ad_inpaint_width": 512,
                        "ad_inpaint_height": 512,
                        "ad_use_steps": True,
                        "ad_steps": 28,
                        "ad_use_cfg_scale": False,
                        "ad_cfg_scale": 7.0,
                        "ad_use_sampler": False,
                        "ad_sampler": "DPM++ 2M Karras",
                        "ad_use_noise_multiplier": False,
                        "ad_noise_multiplier": 1.0,
                        "ad_use_clip_skip": False,
                        "ad_clip_skip": 1,
                        "ad_restore_face": False,
                        "ad_controlnet_model": "None",
                        "ad_controlnet_module": None,
                        "ad_controlnet_weight": 1.0,
                        "ad_controlnet_guidance_start": 0.0,
                        "ad_controlnet_guidance_end": 1.0,
                    }
                ]
            },
        }
        self._hires_draw_parameters["alwayson_scripts"] = deepcopy(plugin_adetailer)
        self._draw_parameters["alwayson_scripts"] = deepcopy(plugin_adetailer)

    def txt2img_and_save(self, in_file_name='output'):
        print('请求服务器中...')
        para=None
        if self.hires_img:
            para = self._hires_draw_parameters
        else:
            para = self._draw_parameters
        response = requests.post(url=f'{self.url}/sdapi/v1/txt2img', json=para)
        json_response = response.json()

        num = 0
        print('服务器已返回.')
        # print('json_response: ', json_response)
        for i in json_response['images']:
            num += 1
            image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))

            png_payload = {
                "image": "data:image/png;base64," + i
            }
            response2 = requests.post(url=f'{self.url}/sdapi/v1/png-info', json=png_payload)

            pnginfo = PngImagePlugin.PngInfo()
            pnginfo.add_text("parameters", response2.json().get("info"))
            image.save(in_file_name+'_'+str(num)+'_'+str(uuid.uuid4())+'.png', pnginfo=pnginfo)

    def txt2img(self):
        print('请求服务器中...')
        para=None
        if self.hires_img:
            para = self._hires_draw_parameters
        else:
            para = self._draw_parameters
        response = requests.post(url=f'{self.url}/sdapi/v1/txt2img', json=para)
        json_response = response.json()

        return Image.open(io.BytesIO(base64.b64decode(json_response['images'][0].split(",", 1)[0])))


    def txt2img_to_clipboard_generator(self):
        import win32clipboard

        print('请求服务器中...')
        para=None
        if self.hires_img:
            para = self._hires_draw_parameters
        else:
            para = self._draw_parameters
        response = requests.post(url=f'{self.url}/sdapi/v1/txt2img', json=para)
        json_response = response.json()

        num = 0
        print('服务器已返回.')
        # print('json_response: ', json_response)
        for i in json_response['images']:
            num += 1
            image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
            output = io.BytesIO()
            image.save(output, 'BMP')
            data = output.getvalue()[14:]

            # 复制到clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
            yield data

    def txt2img_generator(self):
        para=None
        if self.hires_img:
            para = self._hires_draw_parameters
        else:
            para = self._draw_parameters
        response = requests.post(url=f'{self.url}/sdapi/v1/txt2img', json=para)
        json_response = response.json()

        num = 0
        # print(f'======image info======: {json_response}')
        print(f"======images parameter======: {json_response['parameters']}")
        print(f"======images info======: {json_response['info']}")
        for i in json_response['images']:
            # img = io.BytesIO(base64.b64decode(i.split(",", 1)[0]))
            # print(f'======image======: {img}')
            # yield img

            # print(f'======image======: {i}')
            yield i

            # num += 1
            # image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
            #
            # png_payload = {
            #     "image": "data:image/png;base64," + i
            # }
            # response2 = requests.post(url=f'{self.url}/sdapi/v1/png-info', json=png_payload)
            #
            # pnginfo = PngImagePlugin.PngInfo()
            # pnginfo.add_text("parameters", response2.json().get("info"))
            #
            # gen 返回本次png图片的PngInfo
            # print(f"txt2img_generator yield: {pnginfo}")
            # yield pnginfo

    # def txt2video(self, in_file_name='gif_output'):
    #     prompt = deepcopy(self._draw_parameters)
    #     plugin_animatediff = {
    #         'args': [{
    #             # True,           # 正规方式这里应该打开注释，但是这样server生成的png位置不对，生成视频会失败
    #             'enabled': True,  # 这里其实不对，但是这样写生成视频能成功
    #         }]
    #     }
    #     prompt["alwayson_scripts"]['AnimateDiff'] = plugin_animatediff
    #
    #     try:
    #         print(f'API调用: \t"{self.url}/sdapi/v1/txt2img"')
    #         response = requests.post(url=f'{self.url}/sdapi/v1/txt2img', json=prompt)
    #         json_response = response.json()
    #     except Exception as e:
    #         print('txt2video() exception: ', e)
    #
    #     json_response = response.json()
    #     num = 0
    #     print('服务器已返回.')
    #     # print('json_response: ', json_response)
    #     for i in json_response['images']:
    #         num += 1
    #         # image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
    #
    #         print('gif文件长度: ', len(base64.b64decode(i)))
    #         file = open(in_file_name+'_'+str(num)+'_'+str(uuid.uuid4())+'.gif', 'wb')
    #         file.write(base64.b64decode(i))
    #         # file.write(base64.b64decode(i.split(",", 1)[0]))
    #         file.close()
    #
    #         # png_payload = {
    #         #     "image": "data:image/gif;base64," + i
    #         # }
    #         # response2 = requests.post(url=f'{self.url}/sdapi/v1/png-info', json=png_payload)
    #         #
    #         # pnginfo = PngImagePlugin.PngInfo()
    #         # pnginfo.add_text("parameters", response2.json().get("info"))
    #         # image.save(in_file_name+str(num)+'.gif', pnginfo=pnginfo)
    #
    #     if self.restore_face_by_adetailer:
    #         print('插件AnimateDiff和Adetailer冲突，需要重启SD webui服务，重启约30秒后恢复正常。')
    #         self.restart_server_by_api()

    def txt2video(self, in_file_name='gif_output'):
        print('===进入txt2video===')
        os.environ['SD_WEBUI_RESTART'] = 'True' # 用于重启sd webui
        prompt = deepcopy(self._draw_parameters)
        plugin_animatediff = {
            'args': [{
                'enable': True,  # enable AnimateDiff
                'video_length': 16,  # video frame number, 0-24 for v1 and 0-32 for v2
                'format': ['GIF', 'MP4'],  # 'GIF' | 'MP4' | 'PNG' | 'TXT'
                'loop_number': 0,  # 0 = infinite loop
                'fps': 8,  # frames per second
                'model': 'mm_sd_v15_v2.ckpt',  # motion module name
                'reverse': [],  # 0 | 1 | 2 - 0: Add Reverse Frame, 1: Remove head, 2: Remove tail
                # parameters below are for img2gif only.
                'latent_power': 1,
                'latent_scale': 32,
                'last_frame': None,
                'latent_power_last': 1,
                'latent_scale_last': 32
            }]
        }
        prompt["alwayson_scripts"]['AnimateDiff'] = plugin_animatediff

        try:
            print(f'=========API调用: \t"{self.url}/sdapi/v1/txt2img"=========')
            response = requests.post(url=f'{self.url}/sdapi/v1/txt2img', json=prompt)
            # json_response = response.json()
        except Exception as e:
            print('========txt2video() exception: ========', e)

        print('=====服务器已返回.=====')
        # print('json_response: ', json_response)

        # ==============================目前返回的是16个静态图片而非gif或mp4，视频可以直接到sd的output\animatediff里找===============================================
        # json_response = response.json()
        # num = 0
        # for i in json_response['images']:
        #     num += 1
        #     # image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))

            # print('gif文件长度: ', len(base64.b64decode(i)))
            # file = open(in_file_name+'_'+str(num)+'_'+str(uuid.uuid4())+'.gif', 'wb')
            # file.write(base64.b64decode(i))
            # # file.write(base64.b64decode(i.split(",", 1)[0]))
            # file.close()
        # ==============================目前返回的是16个静态图片而非gif或mp4，视频可以直接到sd的output\animatediff里找===============================================

            # png_payload = {
            #     "image": "data:image/gif;base64," + i
            # }
            # response2 = requests.post(url=f'{self.url}/sdapi/v1/png-info', json=png_payload)
            #
            # pnginfo = PngImagePlugin.PngInfo()
            # pnginfo.add_text("parameters", response2.json().get("info"))
            # image.save(in_file_name+str(num)+'.gif', pnginfo=pnginfo)

        print(f'self.restore_face_by_adetailer: {self.restore_face_by_adetailer}')
        if self.restore_face_by_adetailer:
            print('=====插件AnimateDiff和Adetailer冲突，需要重启SD webui服务，重启约10秒后恢复正常。=====')
            self.restart_server_by_api()

    def restart_server_by_api(self):
        try:
            print(f'API调用: \t"{self.url}/sdapi/v1/server-restart"')
            res = requests.post(url=f"{self.url}/sdapi/v1/server-restart", json={})
            print(f'restart_server_by_api() res={res}')
        except Exception as e:
            print('SD webui服务重启中...')
            # print('SD webui服务重启捕获异常: ', e)
        import time
        time.sleep(13)  # 根据经验，大约需要30秒重启时间

    @staticmethod
    def quick_start(in_prompt, in_high_quality=False, in_video=False, in_l_size=768, in_s_size=512):
        import sys
        if sys.platform.startswith('win'):
            file_name = 'd:/sd_pics/output'
        else:
            file_name = '/Users/tutu/sd_pics/output'


        sd = Stable_Diffusion(in_model="awportrait_v11.safetensors", in_url="http://116.62.63.204:5000")
        sd.init()
        sd.set_prompt(
            in_hires_img=in_high_quality,  # 仅对image有效
            # in_hires_img=True,  # 仅对image有效

            in_restore_face_by_adetailer=True,
            in_vertical=True,
            in_steps=20,
            in_batch_size=1,
            in_sampler='DPM++ 2M Karras',
            in_cfg_scale=7,
            in_l_size=in_l_size,
            in_s_size=in_s_size,

            in_prompt=in_prompt,
            in_negative_prompt='(lowres:1.5),(worst quality:2),(low quality:2),(normal quality:2), (text:2), watermark,badhandv4,ng_deepnegative_v1_75t',
        )

        if not in_video:
            sd.txt2img_and_save(in_file_name=file_name)  # output1.png、output2.png...
            # sd.txt2img_to_clipboard_generator()
        elif in_video:
            sd.txt2video(in_file_name=file_name)

    @staticmethod
    def quick_get_image(in_prompt, in_high_quality=False, in_video=False):
        import sys
        # sd = Stable_Diffusion(in_model="dreamshaper_8.safetensors", in_url="http://116.62.63.204:5000")
        # sd = Stable_Diffusion(in_model="majicmixRealistic_betterV2V25.safetensors", in_url="http://116.62.63.204:5000")
        sd = Stable_Diffusion(in_model="awportrait_v11.safetensors", in_url="http://116.62.63.204:5000")
        sd.init()
        sd.set_prompt(
            in_hires_img=in_high_quality,  # 仅对image有效
            # in_hires_img=True,  # 仅对image有效

            in_restore_face_by_adetailer=True,
            in_vertical=True,
            in_steps=20,
            in_batch_size=1,
            in_sampler='DPM++ 2M Karras',
            in_cfg_scale=7,
            in_l_size=768,
            in_s_size=512,

            in_prompt=in_prompt,
            in_negative_prompt='(lowres:1.5),(worst quality:2),(low quality:2),(normal quality:2), (text:2), watermark,badhandv4,ng_deepnegative_v1_75t',
        )

        img = sd.txt2img()
        return img

def main():
    # restartable1 = bool(os.environ.get('SD_WEBUI_RESTART'))
    # os.environ['SD_WEBUI_RESTART'] = 'True'
    # restartable2 = bool(os.environ.get('SD_WEBUI_RESTART'))
    # print(f'SD_WEBUI_RESTART: {os.environ.get("SD_WEBUI_RESTART")}')
    # print(f'restartable1: {restartable1}')
    # print(f'restartable2: {restartable2}')
    while True:
        Stable_Diffusion.quick_start(
            'highest quality,(masterpiece:1.2),High detail RAW color photo,extremely detailed 8k wallpaper,(photo realism:1.3),1girl, (from below:1.3), look straight ahead, smile, (thin waist), (catwalk:1.5), high heels, long shot,  (standing:1.5), full body, pure orange wall background, super model,long slim legs,black hair,(real skin, ultra detailed, 8k, photo realism),random seductive pose,environment light,photon mapping,radiosity,physically-based rendering',
            # 'highest quality,(masterpiece:1.2),extremely detailed 8k wallpaper,(photo realism:1.3),1girl, nipples,topless, (thin waist), white microskirt and hip, stand still, on the beach, white cloud, super model,long slim legs, high heels,black hair,(perfect face, real skin, ultra detailed, 8k, photo realism),(extremely beautiful eyes, blue eyes, ultra detailed, 8k),full body',
            in_high_quality=False,
            in_video=True,
            # in_l_size=1024,
            # in_s_size=768
        )
    # Stable_Diffusion.quick_start('highest quality,(masterpiece:1.2),High detail RAW color photo,extremely detailed 8k wallpaper,(photo realism:1.3),1girl, (from below:1.3), look straight ahead, smile, (thin waist), (catwalk:1.5), high heels, long shot,  (standing:1.5), full body, pure orange wall background, super model,long slim legs,black hair,(real skin, ultra detailed, 8k, photo realism),random seductive pose,environment light,photon mapping,radiosity,physically-based rendering', in_high_quality=True)
    # # sd = Stable_Diffusion(in_model="dreamshaper_8.safetensors", in_url="http://localhost:5000")
    # sd = Stable_Diffusion(in_model="awportrait_v11.safetensors", in_url="http://localhost:5000")
    # # sd = Stable_Diffusion(in_model="awportrait_v11.safetensors")
    # # sd = Stable_Diffusion(in_model="majicmixRealistic_betterV2V25.safetensors", in_url="http://powerai.cc:5000")
    # sd.init()
    # sd.set_prompt(
    #     in_hires_img=False,  # 仅对image有效
    #     # in_hires_img=True,  # 仅对image有效
    #
    #     in_restore_face_by_adetailer=True,
    #     in_vertical=True,
    #     in_steps=20,
    #     in_batch_size=1,
    #     in_sampler='DPM++ 2M Karras',
    #     in_cfg_scale=7,
    #     in_l_size=768,
    #     in_s_size=512,
    #
    #     in_prompt='highest quality,(masterpiece:1.2),High detail RAW color photo,extremely detailed 8k wallpaper,(photo realism:1.3),1girl, (from below:1.3), look straight ahead, smile, (thin waist), (catwalk:1.5), high heels, long shot,  (standing:1.5), full body, pure orange wall background, super model,long slim legs,black hair,(real skin, ultra detailed, 8k, photo realism),random seductive pose,environment light,photon mapping,radiosity,physically-based rendering',
    #     in_negative_prompt='(lowres:1.5),(worst quality:2),(low quality:2),(normal quality:2), (text:2), watermark,badhandv4,ng_deepnegative_v1_75t',
    # )
    #
    # import uuid
    # # print('========================set prompt is: ', sd._draw_parameters)
    # sd.txt2img_and_save(in_file_name='C:/Users/tutu/webui/webui/outputs/txt2img-images/AnimateDiff/output'+str(uuid.uuid4()))   # output1.png、output2.png...
    # # sd.txt2img_to_clipboard_generator()
    #
    # # while True:
    # #     sd.txt2video(in_file_name='gif_output')

if __name__ == "__main__":
    main()