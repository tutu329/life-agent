from config import dred, dgreen, dcyan, dblue, dyellow, dblack, dwhite, dmagenta, dlightblack, dlightblue, dlightred, dlightgreen, dlightyellow, dlightcyan, dlightwhite, dlightmagenta
import config

class Todo_List:
    def __init__(self, title, todo_list):
        self.title = title
        self.todo_list = todo_list
        self.finished_list = [False]*len(self.todo_list)
        self.working_list = [False]*len(self.todo_list)

    def working(self, index):
        if index >= len(self.todo_list) or index < 0:
            return

        self.working_list[index] = True

    def finish(self, index):
        if index >= len(self.todo_list) or index < 0:
            return

        self.finished_list[index] = True

    def print_list(self):
        config.Global.app_debug = True

        # 标题
        dlightgreen('⏺', end='')
        dred(f' {self.title}')

        # todo_list
        i = 0
        for item in self.todo_list:
            if i==0:
                head = '   ⎿ '
            else:
                head = ' ' * 5
            dlightblack(head, end='')

            if self.finished_list[i]:
                # 完成的item
                dlightgreen(f'■ {item}')
            elif self.working_list[i]:
                dlightcyan(f'□ {item}')
            else:
                # 其他item
                dlightblack(f'□ {item}')

            i += 1

        config.Global.app_debug = False

def print_todo_list(title, tode_list, index):
    config.Global.app_debug = True

    print('   ⎿ ■▪▫□◌●◦□└ ┘┌ ┐─│──')

#
# ⏺ Write(index.html)
# ╭─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
# │ Create file                                                                                                         │
# │ ╭─────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮ │
# │ │ index.html                                                                                                      │ │
# │ │ </html>                                                                                                         │ │
# │ ╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯ │
# │ Do you want to create index.html?                                                                                   │
# │ ❯ 1. Yes                                                                                                            │
# │   2. Yes, and don't ask again this session (shift+tab)                                                              │
# │   3. No, and tell Claude what to do differently (esc)                                                               │
# │                                                                                                                     │
# ╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
def print_color():
    config.Global.app_debug = True
    dwhite('⏺', end='')
    dlightwhite('⏺', end='')

    dcyan('⏺', end='')
    dlightcyan('⏺', end='')

    dmagenta('⏺', end='')
    dlightmagenta('⏺', end='')

    dyellow('⏺', end='')
    dlightyellow('⏺', end='')

    dgreen('⏺', end='')
    dlightgreen('⏺', end='')

    dblue('⏺', end='')
    dlightblue('⏺', end='')

    dred('⏺', end='')
    dlightred('⏺', end='')

    dblack('⏺', end='')
    dlightblack('⏺')


if __name__ == "__main__":
    print_color()

    todo_list = [
        'Create HTML structure for chat page',
        'Add CSS styling for chat interface',
        'Implement JavaScript for chat functionality'
    ]

    # print_todo_list('Update Todos', todo_list, 1)

    l = Todo_List(title='Update Todos', todo_list=todo_list)
    l.working(0)
    l.finish(1)
    # l.working(2)
    l.print_list()

    dgreen('finished.')