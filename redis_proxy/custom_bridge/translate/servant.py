from config import dred, dgreen

def translate_servant(
    bridge_type,
    bridge_io_type,
    bridged_command,
    bridged_command_args,
):
    dred(f'bridge_type: {bridge_type}')
    dred(f'bridge_io_type: {bridge_io_type}')
    dred(f'bridged_command: {bridged_command}')
    dred(f'bridged_command_args: {bridged_command_args}')

    pass