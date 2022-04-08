"""
1. Написать функцию host_ping(), в которой с помощью утилиты ping будет проверяться доступность сетевых узлов.
Аргументом функции является список, в котором каждый сетевой узел должен быть представлен именем хоста или ip-адресом.
В функции необходимо перебирать ip-адреса и проверять их доступность с выводом соответствующего сообщения
(«Узел доступен», «Узел недоступен»). При этом ip-адрес сетевого узла должен создаваться с помощью функции ip_address().
"""
from subprocess import call, PIPE
import platform
from ipaddress import ip_address
import threading

res_dict = {'Доступные узлы': [], 'Недоступные узлы': []}


def check_ip_address(arg):
    try:
        ipv4 = ip_address(arg)
    except ValueError:
        raise Exception('Некорректный ip адрес.')
    return ipv4


def ping(ipv4, res_dict, get_list):
    count_param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ('ping', count_param, '1', str(ipv4))
    return_code = call(command, stdout=PIPE)
    if return_code == 0:
        res_dict['Доступные узлы'].append(ipv4)
        res_string = f'{ipv4} - Узел доступен.'
    else:
        res_dict['Недоступные узлы'].append(ipv4)
        res_string = f'{ipv4} - Узел недступен.'
    if not get_list:
        print(res_string)


def host_ping(hosts_list, get_list=False):
    threads = []
    for host in hosts_list:
        try:
            ipv4 = check_ip_address(host)
        except Exception as e:
            print(f'{host} - {e} Узел воспринимается, как доменное имя.')
            ipv4 = host

        thread = threading.Thread(target=ping, args=(ipv4, res_dict, get_list), daemon=True)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    if get_list:
        return res_dict


if __name__ == '__main__':
    hosts_list = ['192.168.1.100', '192.168.1.103', 'mail.ru', '192.168.1.105']
    host_ping(hosts_list)
