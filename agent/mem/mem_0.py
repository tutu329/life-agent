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
    3、qdrant新建一个collection(如mem_collection)，防止报dim应为1536(qdrant默认collection mem0即为1536)却为1024（如m3e的dim为1024）的错
        vi qdrant_create_collection.sh
curl -X PUT 'http://localhost:7872/collections/mem_collection' -H 'Content-Type: application/json' --data-raw '{ "vectors": { "size": 1024, "distance": "Cosine" } }'
        chmod +x qdrant_create_collection.sh
        ./qdrant_create_collection.sh
        http://powerai.cc:7872/dashboard可以看到新建的collection
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
                    "host": "localhost",
                    # "host": "powerai.cc",
                    "port": 7872,
                    "embedding_model_dims":1024,
                    "collection_name":"mem_collection",
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
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": "m3e",
                    "embedding_dims": 1024,
                    "openai_base_url": 'http://localhost:7870/v1'
                    # "openai_base_url": 'http://powerai.cc:7870/v1'
                }
            },
            # "version": "v1.1"
        }

        print(f'-------------mem0 config----------------')
        print(config)
        print(f'------------/mem0 config----------------')
        self.mem_obj = Memory.from_config(config_dict=config)
        print(f'Mem_0.init() invoked.(id: {self.id!r})')

    def add_mem(
            self,
            user_id='default_user',
            category="用户基本信息",
            messages=[
                {"role": "user", "content": "我叫土土"},
                {"role": "assistant", "content": "你好，土土，很高兴认识你！"},
                {"role": "user", "content": "我家在杭州"},
                {"role": "assistant", "content": "杭州是个很美丽的地方！"}
            ],
    ):
        # Store inferred memories (default behavior)
        result=self.mem_obj.add(messages, user_id=user_id, metadata={"category": category})

        # Store raw messages without inference
        # result = m.add(messages, user_id=user_id, metadata={"category": category}, infer=False)
        return result

    def get_related_memories(
            self,
            question,
            user_id='default_user',
    ):
        related_memories = self.mem_obj.search(query=question, user_id=user_id)

        # from pprint import pprint
        # pprint(f'related_memories: {related_memories!r}')
        return related_memories

    def get_all_memories(self, user_id='default_user'):
        all_memories = self.mem_obj.get_all(user_id=user_id)
        return all_memories

