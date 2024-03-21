from pathlib import Path
from tempfile import NamedTemporaryFile

import docker
from docker.errors import DockerException, ImageNotFound
from docker.models.containers import Container as DockerContainer

HOST_WORK_DIR = '/home/tutu/jupyter_temp'
HOST_WORK_DIR2 = '/home/tutu/jupyter_temp'

DOCKER_WORK_DIR = '/usr/local/jupyter_temp'

DEBUG = True

def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)
    else:
        pass

def execute_python_code_in_docker(code: str) -> str:
    """Create and execute a Python file in a Docker container and return the STDOUT of the
    executed code. If there is any data that needs to be captured use a print statement

    Args:
        code (str): The Python code to run
        name (str): A name to be given to the Python file

    Returns:
        str: The STDOUT captured from the code when it ran
    """

    print(f'execute_python_code_in_docker() try to invoke NamedTemporaryFile() withh HOST_WORK_DIR="{HOST_WORK_DIR}"')
    tmp_code_file = None
    error = ''
    try:
        tmp_code_file = NamedTemporaryFile(
            "w", dir=HOST_WORK_DIR, suffix=".py", encoding="utf-8"
        )
        tmp_code_file.write(code)
        tmp_code_file.flush()

        return execute_python_file_in_docker(Path(tmp_code_file.name))
    except Exception as e:
        print('【docker】创建临时python文件报错：', e)
        error = e
    finally:
        if tmp_code_file is not None:
            tmp_code_file.close()
        # return f"系统未返回结果，【docker】创建临时python文件报错: {error}."    # 这行不能有，因为正常return时，finally也会被调用

def execute_python_file_in_docker(
    filename: Path, args: list[str] | str = []
) -> str:
    """Execute a Python file in a Docker container and return the output

    Args:
        filename (Path): The name of the file to execute
        args (list, optional): The arguments with which to run the python script

    Returns:
        str: The output of the file
    """
    # print(f"【docker】Executing python file '{filename}' in docker working directory '{HOST_WORK_DIR}'")

    if isinstance(args, str):
        args = args.split()  # Convert space-separated string to a list

    if not str(filename).endswith(".py"):
        print('【docker】文件错误，打开的不是py文件。')
        return ''

    file_path = filename
    # print('【docker】obj file_path', file_path)
    if not file_path.is_file():
        # Mimic the response that you get from the command line so that it's easier to identify
        print(
            f"【docker】python: 无法打开文件 '{filename}': [Errno 2] No such file or directory"
        )
        return ''

    try:
        dprint(f"【docker】启动docker.from_env()...")
        client = docker.from_env()
        # 如果报错: Error while fetching server API version: ('Connection aborted.', PermissionError(13, 'Permission denied'))
        # 则为当前用户的docker提供权限: sudo usermod -aG docker $USER(需要logout)， 测试：docker ps
        dprint(f"【docker】启动docker.from_env()成功.")
        image_name = "jupyter_with_common_python_libs"
        try:
            client.images.get(image_name)
            dprint(f"【docker】Image文件 '{image_name}' 已打开.")
        except ImageNotFound:
            print(f"【docker】Image文件 '{image_name}' 未找到, 退出.")
            # print(f"【docker】Image文件 '{image_name}' 未找到, pulling from Docker Hub...")
            
            # Use the low-level API to stream the pull response
            # low_level_client = docker.APIClient()
            # for line in low_level_client.pull(image_name, stream=True, decode=True):
            #     # Print the status and progress, if available
            #     status = line.get("status")
            #     progress = line.get("progress")
            #     if status and progress:
            #         print(f"{status}: {progress}")
            #     elif status:
            #         print(status)

        dprint(f"【docker】运行 {file_path} 于 '{image_name}' 容器中...")
        container: DockerContainer = client.containers.run(
            image_name,
            [
                "python",
                "-B",
                file_path.relative_to(HOST_WORK_DIR).as_posix(),
            ]
            + args,
            volumes={
                str(HOST_WORK_DIR): {
                    "bind": "/workspace",
                    "mode": "rw",
                }
            },
            working_dir="/workspace",
            stderr=True,
            stdout=True,
            detach=True,
        )  # type: ignore

        # print('【docker】container obj is: ', container)
        container.wait()
        logs = container.logs().decode("utf-8")
        container.remove()

        # print(f"【docker】Execution complete. Output: {output}")
        # print(f"【docker】Logs: {logs}")

        return logs

    except DockerException as e:
        print('【docker】运行报错: ', e)
        # print("【docker】Could not run the script in a container. If you haven't already, please install Docker https://docs.docker.com/get-docker/")
        return ''

    # def execute_shell(command_line: str, agent: Agent) -> str:
    #     """Execute a shell command and return the output
    #
    #     Args:
    #         command_line (str): The command line to execute
    #
    #     Returns:
    #         str: The output of the command
    #     """
    #     if not validate_command(command_line, agent.legacy_config):
    #         logger.info(f"Command '{command_line}' not allowed")
    #         raise OperationNotAllowedError("This shell command is not allowed.")
    #
    #     current_dir = Path.cwd()
    #     # Change dir into workspace if necessary
    #     if not current_dir.is_relative_to(agent.workspace.root):
    #         os.chdir(agent.workspace.root)
    #
    #     logger.info(
    #         f"Executing command '{command_line}' in working directory '{os.getcwd()}'"
    #     )
    #
    #     result = subprocess.run(command_line, capture_output=True, shell=True)
    #     output = f"STDOUT:\n{result.stdout.decode()}\nSTDERR:\n{result.stderr.decode()}"
    #
    #     # Change back to whatever the prior working dir was
    #     os.chdir(current_dir)
    #
    #     return output
def main():
    code=\
'''
from datetime import datetime

current_date = datetime.now().strftime("%Y-%m-%d")
print(current_date)
'''
    # res = execute_python_code('print("hello")')
    print(f'code: \n{code}')
    res = execute_python_code_in_docker(code)
    print('【docker】运行结果：\n', res)

def main1():
    res = execute_python_code_in_docker('print("hello")')
    print('运行结果：', res)

if __name__ == "__main__":
    main()
