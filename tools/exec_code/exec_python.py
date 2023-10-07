from pathlib import Path
from tempfile import NamedTemporaryFile

import docker
from docker.errors import DockerException, ImageNotFound
from docker.models.containers import Container as DockerContainer

HOST_WORK_DIR = 'D:/jupyter_temp'
HOST_WORK_DIR2 = '/d/jupyter_temp'

DOCKER_WORK_DIR = '/usr/local/jupyter_temp'

def execute_python_code(code: str) -> str:
    """Create and execute a Python file in a Docker container and return the STDOUT of the
    executed code. If there is any data that needs to be captured use a print statement

    Args:
        code (str): The Python code to run
        name (str): A name to be given to the Python file

    Returns:
        str: The STDOUT captured from the code when it ran
    """

    tmp_code_file = NamedTemporaryFile(
        "w", dir=HOST_WORK_DIR, suffix=".py", encoding="utf-8"
    )
    tmp_code_file.write(code)
    tmp_code_file.flush()

    try:
        return execute_python_file(Path(tmp_code_file.name))
    except Exception as e:
        print('执行报错：', e)
    finally:
        tmp_code_file.close()

def execute_python_file(
    filename: Path, args: list[str] | str = []
) -> str:
    """Execute a Python file in a Docker container and return the output

    Args:
        filename (Path): The name of the file to execute
        args (list, optional): The arguments with which to run the python script

    Returns:
        str: The output of the file
    """
    print(
        f"Executing python file '{filename}' in docker working directory '{HOST_WORK_DIR}'"
    )

    if isinstance(args, str):
        args = args.split()  # Convert space-separated string to a list

    if not str(filename).endswith(".py"):
        print('文件错误，打开的不是py文件。')
        return ''

    file_path = filename
    print('obj file_path', file_path)
    if not file_path.is_file():
        # Mimic the response that you get from the command line so that it's easier to identify
        print(
            f"python: 无法打开文件 '{filename}': [Errno 2] No such file or directory"
        )
        return ''

    try:
        client = docker.from_env()
        # You can replace this with the desired Python image/version
        # You can find available Python images on Docker Hub:
        # https://hub.docker.com/_/python
        image_name = "python:3.10"
        try:
            client.images.get(image_name)
            print(f"Image '{image_name}' found locally")
        except ImageNotFound:
            print(
                f"Image '{image_name}' not found locally, pulling from Docker Hub..."
            )
            # Use the low-level API to stream the pull response
            low_level_client = docker.APIClient()
            for line in low_level_client.pull(image_name, stream=True, decode=True):
                # Print the status and progress, if available
                status = line.get("status")
                progress = line.get("progress")
                if status and progress:
                    print(f"{status}: {progress}")
                elif status:
                    print(status)

        print(f"Running {file_path} in a {image_name} container...")
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

        print('container obj is: ', container)
        container.wait()
        logs = container.logs().decode("utf-8")
        container.remove()

        # print(f"Execution complete. Output: {output}")
        # print(f"Logs: {logs}")

        return logs

    except DockerException as e:
        print('docke运行报错: ', e)
        # print(
        #     "Could not run the script in a container. If you haven't already, please install Docker https://docs.docker.com/get-docker/"
        # )
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
    res = execute_python_code('print("hello")')
    print('运行结果：', res)

if __name__ == "__main__":
    main()