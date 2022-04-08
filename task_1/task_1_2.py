"""
2. Написать функцию host_range_ping() для перебора ip-адресов из заданного диапазона. Меняться должен только последний
октет каждого адреса. По результатам проверки должно выводиться соответствующее сообщение.
"""
# from task_1_1 import check_ip_address, host_ping
from task_1_1_thread import check_ip_address, host_ping


def host_range_ping(get_list=False):
    while True:
        first_ip = input('Укажите значение певрого ip адреса: ')
        try:
            ipv4 = check_ip_address(first_ip)
            last_oct = int(first_ip.split('.')[3])
            break
        except Exception as e:
            print(e)
    while True:
        ip_range = input('Укажите диапазон проверяемых адресов: ')
        if not ip_range.isnumeric():
            print('Необходимо ввести число.')
        else:
            if (last_oct + int(ip_range)) > 256:
                print(f'Адреса в диапазоне должны отличаться только последним октетом.\n'
                      f'Количество доступных для провери адресов: {256 - last_oct}')
            else:
                break
    hosts_list = []
    [hosts_list.append(str(ipv4 + i))for i in range(int(ip_range))]
    if not get_list:
        host_ping(hosts_list)
    else:
        return host_ping(hosts_list, get_list=True)


if __name__ == '__main__':
    host_range_ping()
