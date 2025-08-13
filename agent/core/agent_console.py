from config import dred, dgreen, dcyan, dblue, dyellow, dblack, dwhite, dmagenta, dlightblack, dlightblue, dlightred, dlightgreen, dlightyellow, dlightcyan, dlightwhite, dlightmagenta
import config

def print_main():
    config.Global.app_debug = True
    dwhite('⏺')
    dlightwhite('⏺')

    dcyan('⏺')
    dlightcyan('⏺')

    dmagenta('⏺')
    dlightmagenta('⏺')

    dyellow('⏺')
    dlightyellow('⏺')

    dgreen('⏺')
    dlightgreen('⏺')

    dblue('⏺')
    dlightblue('⏺')

    dred('⏺')
    dlightred('⏺')

    dblack('⏺')
    dlightblack('⏺')


if __name__ == "__main__":
    print_main()