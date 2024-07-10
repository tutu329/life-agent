from fake_useragent import UserAgent

ua = UserAgent()
# ua = UserAgent(browsers=['edge', 'chrome'])
print(UserAgent().random)