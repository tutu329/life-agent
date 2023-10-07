logger.debug("AutoGPT is not running in a Docker container")
try:
    client = docker.from_env()
    # You can replace this with the desired Python image/version
    # You can find available Python images on Docker Hub:
    # https://hub.docker.com/_/python
    image_name = "python:3-alpine"
    try:
        client.images.get(image_name)
        logger.debug(f"Image '{image_name}' found locally")
    except ImageNotFound:
        logger.info(
            f"Image '{image_name}' not found locally, pulling from Docker Hub..."
        )
        # Use the low-level API to stream the pull response
        low_level_client = docker.APIClient()
        for line in low_level_client.pull(image_name, stream=True, decode=True):
            # Print the status and progress, if available
            status = line.get("status")
            progress = line.get("progress")
            if status and progress:
                logger.info(f"{status}: {progress}")
            elif status:
                logger.info(status)

    logger.debug(f"Running {file_path} in a {image_name} container...")
    container: DockerContainer = client.containers.run(
        image_name,
        [
            "python",
            "-B",
            file_path.relative_to(agent.workspace.root).as_posix(),
        ]
        + args,
        volumes={
            str(agent.workspace.root): {
                "bind": "/workspace",
                "mode": "rw",
            }
        },
        working_dir="/workspace",
        stderr=True,
        stdout=True,
        detach=True,
    )  # type: ignore

    container.wait()
    logs = container.logs().decode("utf-8")
    container.remove()

    # print(f"Execution complete. Output: {output}")
    # print(f"Logs: {logs}")

    return logs

except DockerException as e:
    logger.warn(
        "Could not run the script in a container. If you haven't already, please install Docker https://docs.docker.com/get-docker/"
    )
    raise CommandExecutionError(f"Could not run the script in a container: {e}")