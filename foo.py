try:
    raise TimeoutError("Something went wrong")
except Exception as e:
    print(type(e))
    print(e)