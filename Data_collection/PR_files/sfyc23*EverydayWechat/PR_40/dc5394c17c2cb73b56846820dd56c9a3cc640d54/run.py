from GFWeather import GFWeather


def run():
    '''
    ä¸»ç¨åºå¥å£
    :return:
    '''
    GFWeather().run()


def test_run():
    '''
    è¿è¡åçæµè¯
    :return:
    '''
    GFWeather().start_today_info(is_test=True)

if __name__ == '__main__':
    # test_run()
    run()



