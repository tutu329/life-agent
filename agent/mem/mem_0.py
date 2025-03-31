from agent.mem.mem_base import Mem_Base
import os
from mem0 import Memory

os.environ["OPENAI_API_KEY"] = "empty"
os.environ["OPENAI_BASE_URL"] = "https://powerai.cc:8001/v1"

class Mem_0(Mem_Base):
    '''
    1、安装mem0:
        pip install mem0ai
    2、安装向量库:
        vi qdrant.sh
sudo docker pull qdrant/qdrant
sudo docker run -p 7872:6333 -p 7873:6334 -v $(pwd)/qdrant_storage:/qdrant/storage:z qdrant/qdrant
        chmod +x qdrant.sh
        ./qdrant.sh

    '''
    def __init__(self):
        super().__init__()
        self.mem_obj = None

    def init(self):
        config = {
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "gpt-4",
                    "temperature": 0.2,
                    "max_tokens": 1500,
                    "api_key": 'empty',
                    "openai_base_url": 'https://powerai.cc:8001/v1'
                }

            },
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    # "host": "localhost",
                    "host": "powerai.cc",
                    # "port": 6333,
                    "port": 7872,
                }
            },
            # "graph_store": {
            #     "provider": "neo4j",
            #     "config": {
            #         "url": "bolt://localhost:7687",
            #         "username": "neo4j",
            #         "password": "**",
            #         "embedding_model_dims": 1536
            #     }
            # },
            # "embedder": {
            #     "provider": "openai",
            #     "config": {
            #         "model": "text-embedding-3-small",
            #         "embedding_dims": 256,
            #     }
            # },
            # "version": "v1.1"
        }

        print(f'-------------mem0 config----------------')
        print(config)
        print(f'------------/mem0 config----------------')
        self.mem_obj = Memory.from_config(config_dict=config)
        print(f'Mem_0.init() invoked.(id: {self.id!r})')

    def get_related_memories(
            self,
            question,
            user_id='tutu',
            category="basic type",
            # category="用户基本信息",
            messages = [
                {"role": "user", "content": "我叫土土"},
                {"role": "assistant", "content": "你好，土土，很高兴认识你！"},
                {"role": "user", "content": "我家在杭州"},
                {"role": "assistant", "content": "杭州是个很美丽的地方！"}
            ]
    ):
        m1 = [
            {"role": "user", "content": "我叫土土"},
            {"role": "assistant", "content": "你好，土土，很高兴认识你！"},
            {"role": "user", "content": "我家在杭州"},
            {"role": "assistant", "content": "杭州是个很美丽的地方！"}
        ]
        # Store inferred memories (default behavior)
        print(f'----------------1--------------------')
        result = self.mem_obj.add(m1, user_id=user_id)
        # result = self.mem_obj.add(m1, user_id=user_id, metadata={"category": category})

        # Store raw messages without inference
        # result = m.add(messages, user_id=user_id, metadata={"category": category}, infer=False)

        # all_memories = m.get_all(user_id=user_id)

        print(f'----------------2--------------------')
        related_memories = self.mem_obj.search(query=question, user_id=user_id)

        print(f'----------------3--------------------')
        print(f'related_memories: {related_memories!r}')
        return related_memories
