#zv#
import os
import time
import shutil
import datetime as dt
from distutils.dir_util import copy_tree
from multiprocessing.pool import ThreadPool as Pool

import psycopg2
from colorama import init, Fore, Style


intro = ['',
         '██████╗░██╗░░░██╗██████╗░██╗░░░██╗███╗░░██╗███╗░░██╗███████╗██████╗░',
         '██╔══██╗╚██╗░██╔╝██╔══██╗██║░░░██║████╗░██║████╗░██║██╔════╝██╔══██╗',
         '██████╔╝░╚████╔╝░██████╔╝██║░░░██║██╔██╗██║██╔██╗██║█████╗░░██████╔╝',
         '██╔═══╝░░░╚██╔╝░░██╔══██╗██║░░░██║██║╚████║██║╚████║██╔══╝░░██╔══██╗',
         '██║░░░░░░░░██║░░░██║░░██║╚██████╔╝██║░╚███║██║░╚███║███████╗██║░░██║',
         '╚═╝░░░░░░░░╚═╝░░░╚═╝░░╚═╝░╚═════╝░╚═╝░░╚══╝╚═╝░░╚══╝╚══════╝╚═╝░░╚═╝',
         '',
         '--------------------------------------------------------------------',
         '',
         'VERSION 1.03',
         '',
         '--------------------------------------------------------------------',
         ]


help_outro = '\n[+]\n\ncopyf - Копировать файл по диапазону аптек/альфамедов\n'\
             'copyd - Копировать папку по диапазону аптек/альфамедов\n'\
             'logs - Проверить размер и дату изменения файла лога бэкапа .txt\n'\
             'backup - Проверить дату последнего бэкапа\n'\
             'date - Проверить дату релиза РПТК\n'\
             'repl - Проверить состояние выполнения репликации'


init()


class Generator:
    """
Класс генеатора создает ip адреса и database имена для аптек/альфамедов по диапазону,
если диапазон не указан создаются все адреса и имена по умолчанию аптеки(1-80) альфамеды(101-110)
    """
    def __init__(self):
        self.first_server = 1; self.last_server = 80
        self.first_alfamed = 101; self.last_alfamed = 110; self.pool_size = 10
        self.servers_buffer = []; self.routers_buffer = []; self.servers_alfamed = []
        self.routers_alfamed = []; self.database_servers = []; self.database_alfamed = []
        self.closed_alfameds = {107}; self.closed_servers = {57, 65, 66, 71, 76}; bad_conn = {5, 46, 59, 74}

    def gen_ip_list(self, start=None, end=None):
        if not start or not end:
            self.gen_ip_list(self.first_server, self.last_server)
        else:
            if start < self.first_server:
                raise ValueError('The pharmacy number is not in the range 1-80')
            elif end > self.last_server:
                raise ValueError('The pharmacy number is not in the range 1-80')
            else:
                for i in range(start, end+1):
                    if i not in self.closed_servers:
                        server_ip = '192.168.{}.51'.format(i)
                        router_ip = '192.168.{}.50'.format(i)
                        self.servers_buffer.append(server_ip)
                        self.routers_buffer.append(router_ip)
                return self.servers_buffer
                return self.routers_buffer

    def gen_alf_ip_list(self, start=None, end=None):
        if not start or not end:
            self.gen_alf_ip_list(self.first_alfamed, self.last_alfamed)
        else:
            if start < self.first_alfamed:
                raise ValueError('The pharmacy number is not in the range 101-110')
            elif end > self.last_alfamed:
                raise ValueError('The pharmacy number is not in the range 101-110')
            else:
                for i in range(start, end+1):
                    if i not in self.closed_alfameds:
                        if i == 102:
                            server_ip = '10.2.2.2'
                            router_ip = '10.2.2.1'
                            self.servers_alfamed.append(server_ip)
                            self.routers_alfamed.append(router_ip)
                        else:
                            server_ip = '192.168.{}.51'.format(i)
                            router_ip = '192.168.{}.50'.format(i)
                            self.servers_alfamed.append(server_ip)
                            self.routers_alfamed.append(router_ip)
                return self.servers_alfamed
                return self.routers_alfamed

    def gen_db_name(self, start=None, end=None):
        if not start or not end:
            self.gen_db_name(self.first_server, self.last_server)
        else:
            if start < self.first_server:
                raise ValueError('The pharmacy number is not in the range 1-80')
            elif end > self.last_server:
                raise ValueError('The pharmacy number is not in the range 1-80')
            else:
                for i in range(start, end+1):
                    if i not in self.closed_servers:
                        if i < 10:
                            db_name = 'A0{}'.format(i)
                            self.database_servers.append(db_name)
                        else:
                            db_name = 'A{}'.format(i)
                            self.database_servers.append(db_name)
                return self.database_servers

    def gen_alf_db_name(self, start=None, end=None):
        if not start or not end:
            self.gen_alf_db_name(self.first_alfamed, self.last_alfamed)
        else:
            if start < self.first_alfamed:
                raise ValueError('The pharmacy number is not in the range 101-110')
            elif end > self.last_alfamed:
                raise ValueError('The pharmacy number is not in the range 101-110')
            else:
                for i in range(start, end+1):
                    if i not in self.closed_alfameds:
                        if i < 110:
                            db_name = 'M0{}a'.format(str(i)[2:3])
                            self.database_alfamed.append(db_name)
                        else:
                            db_name = 'M{}a'.format(str(i)[1:3])
                            self.database_alfamed.append(db_name)
                return self.database_alfamed

    def generate_all(self):
        self.gen_ip_list()
        self.gen_alf_ip_list()
        self.gen_db_name()
        self.gen_alf_db_name()

    def clear_buffers(self):
        self.servers_buffer.clear()
        self.routers_buffer.clear()
        self.servers_alfamed.clear()
        self.routers_alfamed.clear()
        self.database_servers.clear()
        self.database_alfamed.clear()


def print_intro():
    for i in intro:
        print(Fore.YELLOW, i)


def create_connection(db_name, db_host):
    connection = None
    try:
        connection = psycopg2.connect(
            database=db_name,
            user='postgres',
            password='postgres',
            host=db_host,
            port='5432',
        )
    except Exception as error:
        print(Fore.RED, error)
    return connection


def execute_query_repl(connection, db_name):
    try:
        cursor = connection.cursor()
        query = "select * from pg_stat_replication"
        cursor.execute(query)
        result = cursor.fetchall()
        if not result:
            print(Fore.RED, db_name + ' репликация остановлена')
        for i in result:
            print(Fore.YELLOW, ' Слейв ' + i[4] + ' в статусе ' + i[9] + ' на мастере ' + db_name)
    except Exception as error:
        print(Fore.RED, error)


def start_check_replication(buffer1):
    for i in buffer1:
        connection = create_connection(i[0], i[1])
        execute_query_repl(connection, i[0])
    print('\nВыполнено')


def copy_file(file_path, file_name, dist_path, ip):
    file_path = os.path.join(file_path, file_name)
    try:
        path_ = r'\\{}'.format(ip)
        distination_path = os.path.join(path_, dist_path)
        if os.path.exists(distination_path):
            distination_path_ = os.path.join(distination_path, file_name)
            shutil.copy2(file_path, distination_path_)
            print(Fore.GREEN, 'Копирование завершено успешно {}'.format(ip))
            time.sleep(0.1)
        else:
            os.mkdir(distination_path)
            distination_path_ = os.path.join(distination_path, file_name)
            shutil.copy2(file_path, distination_path_)
            print(Fore.GREEN, 'Была создана новая директория и копирование завершено успешно {}'.format(ip))
            time.sleep(0.1)
            #print(Fore.RED, 'Distination directory not defined')
    except Exception as error:
        print(Fore.RED, error)


def copy_folder(dir_path, dist_path, ip):
    try:
        path_ = r'\\{}'.format(ip)
        distination_path = os.path.join(path_, dist_path)
        copy_tree(dir_path, distination_path)
        print(Fore.GREEN, 'Копирование завершено успешно на {}'.format(ip))
        time.sleep(0.1)
    except Exception as error:
        print(Fore.RED, error)


def check_date_rptk(buffer1, buffer2):
    path = r'RPTK\Apteka_Main.exe'
    path_a = r'RPTKa\Apteka_Main.exe'
    path_b = r'RPTKb\Apteka_Main.exe'
    for i in buffer1:
        try:
            path_ = r'\\{}'.format(i)
            path__ = os.path.join(path_, path)
            buf = dt.datetime.fromtimestamp(os.path.getmtime(path__))
            print(Fore.MAGENTA, 'На {} последний релиз РПТК :'.format(i), buf.strftime("%d-%m-%Y AT %H:%M"))
        except Exception as error:           
            print(Fore.RED, error)
    for i in buffer2:
        try:
            path_ = r'\\{}'.format(i)
            path_a = os.path.join(path_, path_a)
            path_b = os.path.join(path_, path_b)
            buf_1 = dt.datetime.fromtimestamp(os.path.getmtime(path_a))
            print(Fore.MAGENTA, 'На {} последний релиз РПТК :'.format(i), buf_1.strftime("%d-%m-%Y AT %H:%M"))
            buf_2 = dt.datetime.fromtimestamp(os.path.getmtime(path_b))
            print(Fore.MAGENTA, 'На {} последний релиз РПТК :'.format(i), buf_2.strftime("%d-%m-%Y AT %H:%M"))
        except Exception as error:           
            print(Fore.RED, error)


def read_logs(file, coding=None):
    try:
        with open(file, 'r', encoding=coding) as f:
            for i in f.readlines():
                if not i.isspace():
                    print(Fore.CYAN, i.replace('\n', ''))
            f.close()
    except UnicodeDecodeError:
        read_logs(file, coding='utf-8')


def check_date_logs_txt(path):
    try:
        file_time = dt.datetime.fromtimestamp(os.path.getmtime(path))
        print(Fore.MAGENTA, 'Лог .txt был изменен : {}'.format(file_time.strftime("%d-%m-%Y AT %H:%M")))
        print(Fore.WHITE, '------------------------------------------------------------------------')

    except Exception as error:
        print(Fore.RED, error)
        print(Fore.WHITE, '------------------------------------------------------------------------')


def check_logs_backup(buffer1, buffer2):
    path = r'RPTKBackup\RPTKARH\log.txt'
    path_a = r'RPTKBackup\RPTKARH\loga.txt'
    path_b = r'RPTKBackup\RPTKARH\logb.txt'

    oth_logs = [r'\\10.3.4.10\RPTKBackup\RPTKARH\log.txt',
                r'\\10.2.41.1\RPTKBackup\RPTKARH\log_ama.txt',
                r'\\10.2.41.1\RPTKBackup\RPTKARH\log_amb.txt']
                
    for i in buffer1:
        try:
            path_ = r'\\{}'.format(i)
            file = os.path.join(path_, path)
            file_size = os.stat(file).st_size
            if file_size > 0:
                print(Fore.RED, 'В логе бэкапа есть ошибки на : {}'.format(file))
                read_logs(file)
                print(Fore.WHITE, '------------------------------------------------------------------------')
            else:
                print(Fore.GREEN, 'В логе бэкапа ошибок нет на : {}'.format(file))
                check_date_logs_txt(file)
        except Exception as error:
            print(Fore.RED, error)

    for i in buffer2:
        try:
            path_ = r'\\{}'.format(i)
            file_a = os.path.join(path_, path_a)
            file_size_a = os.stat(file_a).st_size
            file_b = os.path.join(path_, path_b)
            file_size_b = os.stat(file_b).st_size
            if file_size_a > 0:
                print(Fore.RED, 'В логе бэкапа есть ошибки на : {}'.format(file_a))
                read_logs(file_a)
                print(Fore.WHITE, '------------------------------------------------------------------------')
            elif file_size_b > 0:
                print(Fore.RED, 'В логе бэкапа есть ошибки на : {}'.format(file_b))
                read_logs(file_b)
                print(Fore.WHITE, '------------------------------------------------------------------------')
            else:
                print(Fore.GREEN, 'В логе бэкапа ошибок нет на : {}'.format(file_a))
                check_date_logs_txt(file_a)
                print(Fore.GREEN, 'В логе бэкапа ошибок нет на : {}'.format(file_b))
                check_date_logs_txt(file_b)
        except Exception as error:
            print(Fore.RED, error)

    for i in oth_logs:
        try:
            file_size = os.stat(i).st_size
            if file_size > 0:
                print(Fore.RED, 'В логе бэкапа есть ошибки на : {}'.format(i))
                read_logs(i)
                print(Fore.WHITE, '------------------------------------------------------------------------')
            else:
                print(Fore.GREEN, 'В логе бэкапа ошибок нет на : {}'.format(i))
                check_date_logs_txt(i)
        except Exception as error:
            print(Fore.RED, error)        


def check_data_backup(ip):
    path = r'RPTKBackup\RPTKARH'
    try:
        path_ = r'\\{}'.format(ip)
        path__ = os.path.join(path_, path)
        dir_list = [os.path.join(path__, x) for x in os.listdir(path__) if x != 'log.txt' and x != 'loga.txt' and x != 'logb.txt']
        if dir_list:
            date_list = [[x, os.path.getmtime(x)] for x in dir_list]
            sort_date_list = sorted(date_list, key=lambda x: x[1], reverse=True)
            last_backup = sort_date_list[0][0]
            name_last_backup = os.path.basename(last_backup)
            time_file = dt.datetime.fromtimestamp(os.path.getmtime(last_backup))
            print(Fore.CYAN, ip + " Последний бэкап был : %s" % time_file.strftime('%Y-%m-%d AT %H:%M'))
            time.sleep(0.1)
    except Exception as error:
        print(Fore.RED, error)


def start():
    try:
        while True:
            g.clear_buffers()
            g.generate_all()
            print(Style.RESET_ALL)
            command = input('\n\nInput help or input command copyf/copyd/logs/backup/date/repl # ')
            if command == 'help':
                print(Fore.GREEN, help_outro)
            elif command == 'logs':
                wp = input('Выбрать место server/router # ')
                if wp == 'server':
                    check_logs_backup(g.servers_buffer, g.servers_alfamed)
                if wp == 'router':
                    check_logs_backup(g.routers_buffer, g.routers_alfamed)
            elif command == 'backup':
                pool = Pool(g.pool_size)
                wp = input('Выбрать место server/router # ')
                if wp == 'server':
                    servers_ip = g.servers_buffer + g.servers_alfamed
                    for i in servers_ip:
                        pool.apply_async(check_data_backup, (i, ))
                    pool.close()
                    pool.join()
                if wp == 'router':
                    routers_ip = g.routers_buffer + g.routers_alfamed
                    for i in routers_ip:
                        pool.apply_async(check_data_backup, (i, ))
                    print('Ждите завершения пула потоков ... ')
                    pool.close()
                    pool.join()
            elif command == 'date':
                wp = input('Выбрать место server/router # ')
                if wp == 'server':
                    check_date_rptk(g.servers_buffer, g.servers_alfamed)
                if wp == 'router':
                    check_date_rptk(g.routers_buffer, g.routers_alfamed)
            elif command == 'repl':
                print('')
                servers_ip = g.servers_buffer + g.servers_alfamed
                servers_db = g.database_servers + g. database_alfamed
                repl_list = [run for run in zip(servers_db, servers_ip)]
                start_check_replication(repl_list)
            elif command == 'copyf':
                g.clear_buffers()
                pool = Pool(g.pool_size)
                wp = input('Выбрать место server/router/server_alf/router_alf/range # ')
                start = int(input('Введите начало диапазона : аптека(1-80)/альфамед(101-110) или введите 0 если используете range # '))
                end = int(input('Введите конец диапазона : аптека(1-80)/альфамед(101-110) или введите 0 если используете range # '))
                file_path = input('Директория копируемого файла # '); file_name = input('Имя файла # '); dist_path = input(r'Директория назначения без первого слэша например: Scripts\bat # ')
                if wp == 'server':
                    g.gen_ip_list(start, end)
                    for i in g.servers_buffer:
                        pool.apply_async(copy_file, (file_path, file_name, dist_path, i, ))
                    pool.close()
                    pool.join()
                if wp == 'router':
                    g.gen_ip_list(start, end)
                    for i in g.routers_buffer:
                        pool.apply_async(copy_file, (file_path, file_name, dist_path, i,))
                    pool.close()
                    pool.join()
                if wp == 'server_alf':
                    g.gen_alf_ip_list(start, end)
                    for i in g.servers_alfamed:
                        pool.apply_async(copy_file, (file_path, file_name, dist_path, i,))
                    pool.close()
                    pool.join()
                if wp == 'router_alf':
                    g.gen_alf_ip_list(start, end)
                    for i in g.routers_alfamed:
                        pool.apply_async(copy_file, (file_path, file_name, dist_path, i,))
                    pool.close()
                    pool.join()
                if wp == 'range':
                    rg = input('Указать аптеки/альфамеды через пробел # ')
                    wh = input('Ввести 1, если сервер и 0 если роутер # ')
                    for i in rg.split(' '):
                        if i != '' and i != ' ':
                            ip_s = '192.168.{}.51'.format(i)
                            ip_r = '192.168.{}.50'.format(i)
                            g.servers_buffer.append(ip_s)
                            g.routers_buffer.append(ip_r)
                    if int(wh) == 1:
                        for s in g.servers_buffer:
                            pool.apply_async(copy_file, (file_path, file_name, dist_path, s, ))
                        pool.close()
                        pool.join()
                    elif int(wh) == 0:
                        for r in g.routers_buffer:
                            pool.apply_async(copy_file, (file_path, file_name, dist_path, r, ))
                        pool.close()
                        pool.join()
            elif command == 'copyd':
                g.clear_buffers()
                pool = Pool(g.pool_size)
                wp = input('Выбрать место server/router/server_alf/router_alf/range # ')
                start = int(input('Введите начало диапазона : аптека(1-80)/альфамед(101-110) или введите 0 если используете range # '))
                end = int(input('Введите конец диапазона : аптека(1-80)/альфамед(101-110) или введите 0 если используете range # '))
                file_path = input('Директория копирования # '); dist_path = input(r'Директория назначения : Scripts\RPTK_release, если директория не существует, она будет создана # ')
                if wp == 'server':
                    g.gen_ip_list(start, end)
                    for i in g.servers_buffer:
                        pool.apply_async(copy_folder, (file_path, dist_path, i, ))
                    pool.close()
                    pool.join()
                if wp == 'router':
                    g.gen_ip_list(start, end)
                    for i in g.routers_buffer:
                        pool.apply_async(copy_folder, (file_path, dist_path, i, ))
                    pool.close()
                    pool.join()
                if wp == 'server_alf':
                    g.gen_alf_ip_list(start, end)
                    for i in g.servers_alfamed:
                        pool.apply_async(copy_folder, (file_path, dist_path, i, ))
                    pool.close()
                    pool.join()
                if wp == 'router_alf':
                    g.gen_alf_ip_list(start, end)
                    for i in g.routers_alfamed:
                        pool.apply_async(copy_folder, (file_path, dist_path, i, ))
                    pool.close()
                    pool.join()
                if wp == 'range':
                    rg = input('Указать аптеки/альфамеды через пробел # ')
                    wh = input('Ввести 1, если сервер и 0 если роутер # ')
                    for i in rg.split(' '):
                        if i != '' and i != ' ':
                            ip_s = '192.168.{}.51'.format(i)
                            ip_r = '192.168.{}.50'.format(i)
                            g.servers_buffer.append(ip_s)
                            g.routers_buffer.append(ip_r)
                    if int(wh) == 1:
                        for i in g.servers_buffer:
                            pool.apply_async(copy_folder, (file_path, dist_path, i, ))
                        pool.close()
                        pool.join()
                    elif int(wh) == 0:
                        for i in g.routers_buffer:
                            pool.apply_async(copy_folder, (file_path, dist_path, i, ))
                        pool.close()
                        pool.join()
            #elif command == 'pgagent':
                #start_check_pgagent()
            else:
                print(Fore.RED, 'Команда не найдена')
    except KeyboardInterrupt:
        print('\n')
        print(Fore.CYAN, 'Выход из программы ...')
        exit()
    except Exception as error:
        print(Fore.RED, error)


if __name__ == '__main__':
    g = Generator()
    print_intro()
    start()
