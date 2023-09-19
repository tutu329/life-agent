from codeinterpreterapi import CodeInterpreterSession, settings
import openai

def main1():
    openai.api_base = "http://116.62.63.204:8000/v1"
    openai.api_key = "none"

    # set api key (or automatically loads from env vars)
    settings.OPENAI_API_KEY = "none"
    settings.MODEL = "Qwen-7B"
    # settings.OPENAI_API_BASE = "http://116.62.63.204:8000/v1"

    # set OPENAI_API_KEY=none
    # set OPENAI_API_BASE=http://116.62.63.204:8000/v1

    # settings.OPENAI_API_TYPE=azure
    # settings.OPENAI_API_VERSION=your_api_version
    # settings.DEPLOYMENT_NAME=your_deployment_name

    # create a session
    with CodeInterpreterSession() as session:
        # generate a response based on user input
        response = session.generate_response(
            "Plot the bitcoin chart of year 2023"
        )

        # output the response
        response.show()

def main():
    from codeinterpreterapi import CodeInterpreterSession, settings
    import os

    openai.api_base = "http://116.62.63.204:8000/v1"
    openai.api_key = "none"
    openai.proxy = os.getenv('https_proxy')
    print('openai.proxy is: ', openai.proxy)

    # set api key (or automatically loads from env vars)
    settings.OPENAI_API_KEY = "none"
    settings.MODEL = "Qwen-7B"


    print(
        "AI: Hello, I am the "
        "code interpreter agent.\n"
        "Ask me todo something and "
        "I will use python to do it!\n"
    )

    with CodeInterpreterSession() as session:
        while True:
            session.generate_response_sync(input("\nUser: ")).show()


if __name__ == "__main__" :
    main()

