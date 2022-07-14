# zv
# Pyrunner 1.0.1
import os
import time
import shutil
import datetime as dt
from datetime import datetime
from distutils.dir_util import copy_tree
from multiprocessing.pool import ThreadPool as Pool
from multiprocessing import Lock

import psycopg2
from colorama import init, Fore, Style, Back

from libfptr10 import IFptr


intro = ['                                                                            ',
         '   ####################################################################     ',
         '                                                                            ',
         '   ██████╗░██╗░░░██╗██████╗░██╗░░░██╗███╗░░██╗███╗░░██╗███████╗██████╗░     ',
         '   ██╔══██╗╚██╗░██╔╝██╔══██╗██║░░░██║████╗░██║████╗░██║██╔════╝██╔══██╗     ',
         '   ██████╔╝░╚████╔╝░██████╔╝██║░░░██║██╔██╗██║██╔██╗██║█████╗░░██████╔╝     ',
         '   ██╔═══╝░░░╚██╔╝░░██╔══██╗██║░░░██║██║╚████║██║╚████║██╔══╝░░██╔══██╗     ',
         '   ██║░░░░░░░░██║░░░██║░░██║╚██████╔╝██║░╚███║██║░╚███║███████╗██║░░██║     ',
         '   ╚═╝░░░░░░░░╚═╝░░░╚═╝░░╚═╝░╚═════╝░╚═╝░░╚══╝╚═╝░░╚══╝╚══════╝╚═╝░░╚═╝     ',
         '                                                                            ',
         '   ####################################################################     ',
         '                                                                            ',
         '   ###########   Памятка для Администраторов РПТК   ###################     ',
         '                                                                            ',
         '   ###########  Утром запусти : logs, backup, repl   ##################     ',
         '                                                                            '
         ]

help_outro = '\n[+]\n\ncopyf - Копировать файл по диапазону аптек/альфамедов\n'\
             'copyd - Копировать папку по диапазону аптек/альфамедов\n'\
             'logs - Проверить ошибки лога бэкапа и дату изменения\n'\
             'backup - Проверить дату последнего бэкапа\n'\
             'date - Проверить дату релиза РПТК (только сервер/роутер)\n'\
             'repl - Проверить состояние выполнения репликации\n'\
             'atol - Проверить инфо на кассах (непереданные чеки, дата ОКП)\n'\
             'ddir - Очистить папку по диапазону аптек/альфамедов\n'\
             'dfile - Удалить файл по диапазону аптек/альфамедов\n'\

profiles = {
    'path_exe': r'RPTK\Apteka_Main.exe',
    'path_aexe': r'RPTKa\Apteka_Main.exe',
    'path_bexe': r'RPTKb\Apteka_Main.exe',
    'path_log': r'RPTKBackup\RPTKARH\log.txt',
    'path_alog': r'RPTKBackup\RPTKARH\loga.txt',
    'path_blog': r'RPTKBackup\RPTKARH\logb.txt',
    'path_bckp': r'RPTKBackup\RPTKARH',
}

SQL_QUERY_REPL = """SELECT 
        client_addr As client, usename AS user, application_name AS name,
        state, sync_state AS mode,
        (pg_wal_lsn_diff(pg_current_wal_lsn(),sent_lsn) / 1024)::int as pending,
        (pg_wal_lsn_diff(sent_lsn,write_lsn) / 1024)::int as write,
        (pg_wal_lsn_diff(write_lsn,flush_lsn) / 1024)::int as flush,
        (pg_wal_lsn_diff(flush_lsn,replay_lsn) / 1024)::int as replay,
        (pg_wal_lsn_diff(pg_current_wal_lsn(),replay_lsn))::int / 1024 as total_lag
        FROM pg_stat_replication;"""


flag_error = False
flag_color = False

none_time = datetime(1970, 1, 1, 0)
today_date = datetime.now().date()

init()

# BEGIN CLASS
class Generator:
    """
Класс генеатора создает ip адреса и database имена для аптек/альфамедов по диапазону,
если диапазон не указан создаются все адреса и имена по умолчанию конечная точка: self.last_server и self.last_alf
    """
    def __init__(self):
        self.names = {
            'servers_buffer': [],
            'routers_buffer': [],
            'servers_alfamed': [],
            'routers_alfamed': [],
            'database_servers': [],
            'database_alfamed': [],
            'atol_buffer': [],
            'other': [],
        }
        self.pool_size = 13
        self.first_server = 1
        self.last_server = 80
        self.first_alf = 1
        self.last_alf = 10
        self.closed = (10, 57, 65, 66, 71, 74, 76, )
        self.closed_alf = (2, 7, )
        self.second_atol = (2, 4, 9, 12, 13, 42, 59, )
        self.third_atol = (30, )
        #self.bad_conn = (5, 46, 59, 74, )
    # генератор адресов аптек
    def generator_apteka(self, start=None, end=None):
        if not start or not end:
            self.generator_apteka(self.first_server, self.last_server)
        else:
            if start < self.first_server:
                raise ValueError('The pharmacy number is not in the range apteka')
            elif end > self.last_server:
                raise ValueError('The pharmacy number is not in the range apteka')
            else:
                self.names['servers_buffer'] = ['192.168.{}.51'.format(i) for i in range(start, end+1) if i not in self.closed] + ['10.3.4.10', '10.2.41.1']
                self.names['routers_buffer'] = ['192.168.{}.50'.format(i) for i in range(start, end+1) if i not in self.closed]
    # генератор адресов альфамедов
    def generator_alfamed(self, start=None, end=None):
        if not start or not end:
            self.generator_alfamed(self.first_alf, self.last_alf)
        else:
            if start < self.first_alf:
                raise ValueError('The pharmacy number is not in the range alfamed')
            elif end > self.last_alf:
                raise ValueError('The pharmacy number is not in the range alfamed')
            else:
                self.names['servers_alfamed'] = ['192.168.10{}.51'.format(i) for i in range(start, 10) if i not in self.closed_alf] + \
                          ['192.168.1{}.51'.format(i) for i in range(10, end+1) if i not in self.closed_alf] + ['10.2.2.2']
                self.names['routers_alfamed'] = ['192.168.10{}.50'.format(i) for i in range(start, 10) if i not in self.closed_alf] + \
                          ['192.168.1{}.50'.format(i) for i in range(10, end+1) if i not in self.closed_alf] + ['10.2.2.1']
    # генератор имен баз данных аптек
    def generator_dbapteka(self, start=None, end=None):
        if not start or not end:
            self.generator_dbapteka(self.first_server, self.last_server)
        else:
            if start < self.first_server:
                raise ValueError('The pharmacy number is not in the range apteka')
            elif end > self.last_server:
                raise ValueError('The pharmacy number is not in the range apteka')
            else:
                self.names['database_servers'] = ['A0{}'.format(i) for i in range(start, 10)] + ['A{}'.format(i) for i in range(10, end+1) if i not in self.closed] + ['AIA', 'AMA']
    # генератор имен баз данных альфамедов
    def generator_dbalfamed(self, start=None, end=None):
        if not start or not end:
            self.generator_dbalfamed(self.first_alf, self.last_alf)
        else:
            if start < self.first_alf:
                raise ValueError('The pharmacy number is not in the range alfamed')
            elif end > self.last_alf:
                raise ValueError('The pharmacy number is not in the range alfamed')
            else:
                self.names['database_alfamed'] = ['M0{}a'.format(i) for i in range(start, 10) if i not in self.closed_alf] + \
                          ['M{}a'.format(i) for i in range(10, end+1) if i not in self.closed_alf] + ['M02a']
    # генератор адресов касс
    def generator_kassa(self):
            self.names['atol_buffer'] = ['192.168.{}.155'.format(i) for i in range(self.first_server, self.last_server+1) if i not in self.closed] + \
                                                     ['192.168.10{}.155'.format(i) for i in range(self.first_alf, 10) if i not in self.closed_alf] + \
                                                     ['192.168.1{}.155'.format(i) for i in range(10, self.last_alf+1) if i not in self.closed_alf] + \
                                                     ['192.168.{}.156'.format(i) for i in self.second_atol] + ['192.168.{}.157'.format(i) for i in self.third_atol]
    # генератор адресов через пробелы
    def generator_random(self, ip_string, server_apt, server_alf, router_apt, router_alf):
        if server_apt:
            g.names['other'] = ['192.168.{}.51'.format(i) for i in ip_string.split(' ') if i != '' and i != ' ']
        elif server_alf:
            g.names['other'] = ['192.168.10{}.51'.format(i) for i in ip_string.split(' ') if  i != '' and i != ' ' and int(i) < 10] + \
                                                    ['192.168.1{}.51'.format(i) for i in ip_string.split(' ') if i != '' and i != ' ' and int(i) >= 10]
        elif router_apt:
            g.names['other'] = ['192.168.{}.50'.format(i) for i in ip_string.split(' ') if i != '' and i != ' ']
        elif router_alf:
            g.names['other'] = ['192.168.10{}.50'.format(i) for i in ip_string.split(' ') if  i != '' and i != ' ' and int(i) < 10] + \
                                        ['192.168.1{}.50'.format(i) for i in ip_string.split(' ') if i != '' and i != ' ' and int(i) >= 10]

    def generator_everything(self):
        self.generator_apteka(), self.generator_alfamed(), self.generator_dbapteka(), self.generator_dbalfamed(), self.generator_kassa()

    def clear_buffer(self):
        self.names.clear()
# END CLASS

def print_intro():
    for i in intro:
        print(Back.CYAN, Fore.BLACK, i)


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

# NO USE def print_result()
def execute_query_repl(connection, db_name):
    try:
        cursor = connection.cursor()
        cursor.execute(SQL_QUERY_REPL)
        result = cursor.fetchall()
        if not result:
            print(Fore.RED, db_name + ' репликация не выполняется')
        for i in result:
            print(Fore.GREEN, 'Слейв ' + i[0] + ' в статусе ' + i[3] + ' на {}'.format(db_name) + \
                ' pending = ' + str(i[5]) + ' write = ' + str(i[6]) + ' flush = ' + str(i[7]) + ' replay = ' + str(i[8]) + ' total_lag = ' + str(i[9]))
    except Exception as error:
        print(Fore.RED, error)


def start_check_replication(buffer1):
    print( 'https://habr.com/ru/company/oleg-bunin/blog/414111/ - источник\n'
           'pending - сколько журналов транзакций сгенерировано на мастере но не отправлено на реплику: проблема - сеть\n'
           'write - сколько реплики отправлено но не записано: проблема бывает редко - возможно диски\n'
           'flush - записано но еще не была выполнена команда fsync: проблема - диски не успевают записывать и проигрывать данные\n'
           'replay - данные сброшены на реплику и выполнен fsync но еще не воспроизведены репликой (см. flush)\n'
           'total_lag - общий суммарный лаг\n')
    for i in buffer1:
        connection = create_connection(i[0], i[1])
        execute_query_repl(connection, i[0])


def copy_file(file_path, file_name, dist_path, ip):
    file_path = os.path.join(file_path, file_name)
    try:
        path_ = r'\\{}'.format(ip)
        distination_path = os.path.join(path_, dist_path)
        if os.path.exists(distination_path):
            distination_path_ = os.path.join(distination_path, file_name)
            shutil.copy2(file_path, distination_path_)
            res = 'Копирование завершено успешно {}'.format(ip)
            lines = '-------------------------------------------'
            print_result(res, lines)
        else:
            os.mkdir(distination_path)
            distination_path_ = os.path.join(distination_path, file_name)
            shutil.copy2(file_path, distination_path_)
            res = 'Была создана новая директория и копирование завершено успешно {}'.format(ip)
            lines = '-------------------------------------------'
            print_result(res, lines)
    except Exception as error:
        flag_error = True
        res = error
        lines = '-------------------------------------------'
        print_result(res, lines, flag=flag_error, flag_=False)


def copy_folder(dir_path, dist_path, ip):
    try:
        path_ = r'\\{}'.format(ip)
        distination_path = os.path.join(path_, dist_path)
        copy_tree(dir_path, distination_path)
        res = 'Копирование завершено успешно {}'.format(ip)
        lines = '----------------------------------------------'
        print_result(res, lines)
    except Exception as error:
        flag_error = True
        res = error
        lines = '----------------------------------------------'
        print_result(res, lines, flag=flag_error, flag_=False)


def delete_file(dist_path, file_name, ip):
    try:
        path_ = r'\\{}'.format(ip)
        distination_path = os.path.join(path_, dist_path)
        if os.path.exists(distination_path):
            os.remove(os.path.join(distination_path, file_name))
            res = 'Файл на {} с именем {} - удален'.format(ip, file_name)
            lines = '-----------------------------------------------'
            print_result(res, lines)
    except Exception as error:
        flag_error = True
        res = error
        lines = '-----------------------------------------------'
        print_result(res, lines, flag=flag_error, flag_=False)


def delete_all_in_folder(dist_path, ip, stop_name=None):
    try:
        path_ = r'\\{}'.format(ip)
        distination_path = os.path.join(path_, dist_path)
        for dirpath, dirnames, filenames in os.walk(distination_path):
            for dirname in dirnames:
                shutil.rmtree(os.path.join(dirpath, dirname))
            for filename in filenames:
                if filename == stop_name:
                    pass
                else:
                    os.remove(os.path.join(dirpath, filename))
        res = 'Директория {} очищена'.format(distination_path)
        lines = '-----------------------------------------------'
        print_result(res, lines)
    except Exception as error:
        flag_error = True
        res = error
        lines = '-----------------------------------------------'
        print_result(res, lines, flag=flag_error, flag_=False)

# NO USE def print_result()
def check_date_rptk(buffer1, buffer2):
    for i in buffer1:
        try:
            path_ = r'\\{}'.format(i)
            path__ = os.path.join(path_, profiles['path_exe'])
            buf = dt.datetime.fromtimestamp(os.path.getmtime(path__))
            print(Fore.GREEN, 'На {} последний релиз РПТК :'.format(path__), buf.strftime("%d-%m-%Y AT %H:%M"))
        except Exception as error:           
            print(Fore.RED, error)
    for i in buffer2:
        try:
            path_ = r'\\{}'.format(i)
            path_a = os.path.join(path_, profiles['path_aexe'])
            path_b = os.path.join(path_, profiles['path_bexe'])
            buf_1 = dt.datetime.fromtimestamp(os.path.getmtime(path_a))
            print(Fore.GREEN, 'На {} последний релиз РПТК :'.format(path_a), buf_1.strftime("%d-%m-%Y AT %H:%M"))
            buf_2 = dt.datetime.fromtimestamp(os.path.getmtime(path_b))
            print(Fore.GREEN, 'На {} последний релиз РПТК :'.format(path_b), buf_2.strftime("%d-%m-%Y AT %H:%M"))
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

# no use def print_result()
def check_date_logs_txt(path):
    try:
        file_time = dt.datetime.fromtimestamp(os.path.getmtime(path))
        if str(file_time.strftime("%Y-%m-%d")) != str(today_date):
            print(Fore.RED, 'Лог был изменен давно : {}'.format(file_time.strftime("%d-%m-%Y AT %H:%M")))
            print(Fore.WHITE, '------------------------------------------------------------------------')
        else:
            #print(Fore.WHITE, 'Лог был изменен : {}'.format(file_time.strftime("%d-%m-%Y AT %H:%M")))
            print(Fore.WHITE, '------------------------------------------------------------------------')

    except Exception as error:
        print(Fore.RED, error)
        print(Fore.WHITE, '------------------------------------------------------------------------')

# NO USE def print_result()
def check_logs_backup(buffer1, buffer2):
    oth_logs = [r'\\10.3.4.10\RPTKBackup\RPTKARH\log.txt', r'\\10.2.41.1\RPTKBackup\RPTKARH\log_ama.txt', r'\\10.2.41.1\RPTKBackup\RPTKARH\log_amb.txt' ]
                
    for i in buffer1:
        try:
            path_ = r'\\{}'.format(i)
            file = os.path.join(path_, profiles['path_log'])
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
            print(Fore.WHITE, '------------------------------------------------------------------------')

    for i in buffer2:
        try:
            path_ = r'\\{}'.format(i)
            file_a = os.path.join(path_, profiles['path_alog'])
            file_size_a = os.stat(file_a).st_size
            file_b = os.path.join(path_, profiles['path_blog'])
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
    try:
        path_ = r'\\{}'.format(ip)
        path__ = os.path.join(path_, profiles['path_bckp'])
        dir_list = [os.path.join(path__, x) for x in os.listdir(path__) if x != 'log.txt' and x != 'loga.txt' and x != 'logb.txt']

        if dir_list:
            date_list = [[x, os.path.getmtime(x)] for x in dir_list]
            sort_date_list = sorted(date_list, key=lambda x: x[1], reverse=True)
            last_backup = sort_date_list[0][0]
            name_last_backup = os.path.basename(last_backup)
            time_file = dt.datetime.fromtimestamp(os.path.getmtime(last_backup))
            if str(time_file.strftime('%Y-%m-%d')) != str(today_date):
                flag_error = True
                res = ip + " Последний бэкап был : %s" % time_file.strftime('%Y-%m-%d AT %H:%M')
                lines = '--------------------------------------------------------'
                print_result(res, lines, flag_error)
            else:
                res = ip + " Последний бэкап был : %s" % time_file.strftime('%Y-%m-%d AT %H:%M')
                lines = '--------------------------------------------------------'
                print_result(res, lines)

    except Exception as error:
        flag_error = True
        res = error
        lines = '--------------------------------------------------------'
        print_result(res, lines, flag=flag_error, flag_=False)


def atol_check(ip, all_output):
    DRIVER_PATH = os.path.join(os.getcwd(), 'fptr10.dll')
    fptr = IFptr(DRIVER_PATH)

    IP = ip
    PORT = '5555'
    SOCKET_KKM = '{}:{}'.format(IP, PORT)

    fptr.setSingleSetting(IFptr.LIBFPTR_SETTING_MODEL, str(IFptr.LIBFPTR_MODEL_ATOL_AUTO))
    fptr.setSingleSetting(IFptr.LIBFPTR_SETTING_PORT, str(IFptr.LIBFPTR_PORT_TCPIP))
    fptr.setSingleSetting(IFptr.LIBFPTR_SETTING_IPADDRESS, IP)
    fptr.setSingleSetting(IFptr.LIBFPTR_SETTING_IPPORT, PORT)
    fptr.applySingleSettings()

    try:
        fptr.open()
        isOpened = fptr.isOpened()
        if isOpened == 0:
            flag_error = True
            res = 'Нет удалось подключиться к {}'.format(SOCKET_KKM)
            lines = '---------------------------------------------------------------------------------------------------------------------------------------------------'
            print_result(res, lines, flag_error)
            write_resul(res, lines)
        else:

            fptr.setParam(IFptr.LIBFPTR_PARAM_DATA_TYPE, IFptr.LIBFPTR_DT_STATUS)
            fptr.queryData()

            NUMBER_KKT = fptr.getParamString(IFptr.LIBFPTR_PARAM_SERIAL_NUMBER)
            # STATUS_STATE = fptr.getParamInt(IFptr.LIBFPTR_PARAM_SHIFT_STATE)
            KKM_TIME = fptr.getParamDateTime(IFptr.LIBFPTR_PARAM_DATE_TIME)

            # Обмен с ОФН
            fptr.setParam(IFptr.LIBFPTR_PARAM_FN_DATA_TYPE, IFptr.LIBFPTR_FNDT_OFD_EXCHANGE_STATUS)
            fptr.fnQueryData()

            NOT_TRANS_DOC = fptr.getParamInt(IFptr.LIBFPTR_PARAM_DOCUMENTS_COUNT)
            DATA_LAST_TRANS = fptr.getParamDateTime(IFptr.LIBFPTR_PARAM_DATE_TIME)
            DATA_FN_KEY = fptr.getParamDateTime(IFptr.LIBFPTR_PARAM_LAST_SUCCESSFUL_OKP)

            # if STATUS_STATE == 0:
            # STATUS_STATE_STR = 'Закрыта'
            # elif STATUS_STATE == 1:
            # STATUS_STATE_STR = 'Открыта'
            # elif STATUS_STATE == 2:
            # STATUS_STATE_STR = 'Истекла'

            if int(NOT_TRANS_DOC) > 0:
                flag_color = True
                if DATA_FN_KEY == none_time:
                    res = '{}; ККТ №: {}; Дата/время: {}; Непереданные чеки: {}; Первый непереданный: {};'.format(SOCKET_KKM, NUMBER_KKT, KKM_TIME, NOT_TRANS_DOC, DATA_LAST_TRANS)
                    lines = '--------------------------------------------------------------------------------------------------------------------------------------------------'
                    print_result(res, lines, flag=False, flag_=flag_color)
                    write_resul(res, lines)
                else:
                    res = '{}; ККМ №: {}; Дата/Время: {}; Непереданные чеки: {}; Первый непереданный: {}; Дата/время последнего ОКП: {};'.format(
                        SOCKET_KKM, NUMBER_KKT, KKM_TIME, NOT_TRANS_DOC, DATA_LAST_TRANS, DATA_FN_KEY)
                    lines = '--------------------------------------------------------------------------------------------------------------------------------------------------'
                    print_result(res, lines, flag=False, flag_=flag_color)
                    write_resul(res, lines)
            else:
                if all_output:
                    if DATA_FN_KEY == none_time:
                        res = '{}; ККТ №: {}; Дата/время: {}; Непереданные чеки: {};'.format(SOCKET_KKM, NUMBER_KKT, KKM_TIME, NOT_TRANS_DOC)
                        lines = '--------------------------------------------------------------------------------------------------------------------------------------------------'
                        print_result(res, lines)
                        write_resul(res, lines)
                    else:
                        res = '{}; ККМ №: {}; Дата/Время: {}; Непереданные чеки: {}; Дата/время последнего ОКП: {};'.format(
                            SOCKET_KKM, NUMBER_KKT, KKM_TIME, NOT_TRANS_DOC, DATA_FN_KEY)
                        lines = '--------------------------------------------------------------------------------------------------------------------------------------------------'
                        print_result(res, lines)
                        write_resul(res, lines)
            # debugger
            # print(fptr.errorDescription())
            fptr.close()

    except Exception as error:
        flag_error = True
        res = error
        lines = '--------------------------------------------------------------------------------------------------------------------------------------------------'
        print(res, lines, flag=flag_error, flag_=False)
        fptr.close()


def write_resul(result, lines):
    with open('log_atol.csv', 'a') as f:
        f.write(result + '\n')
        f.write(lines + '\n')
    f.close()


def print_result(result, lines, flag=None, flag_=None):
    with lock:
        if flag:
            print(Fore.RED, result)
            print(Fore.WHITE, lines)
        elif flag_:
            print(Fore.CYAN, result)
            print(Fore.WHITE, lines)
        else:
            print(Fore.GREEN, result)
            print(Fore.WHITE, lines)

# MAIN METHOD
def start():
    try:
        while True:
            flag_error = False
            flag_color = False
            g.clear_buffer()
            g.generator_everything()
            print(Style.RESET_ALL)
            command = input('\n\nПомощь - help или команда: copyf/copyd/logs/backup/date/repl/atol/ddir/dfile # ')
            if command == 'help':
                print(Fore.CYAN, help_outro)
            elif command == 'logs':
                wp = input('Выбрать место server/router # ')
                if wp == 'server':
                    check_logs_backup(g.names['servers_buffer'], g.names['servers_alfamed'])
                if wp == 'router':
                    check_logs_backup(g.names['routers_buffer'], g.names['routers_alfamed'])
            elif command == 'backup':
                pool = Pool(g.pool_size)
                wp = input('Выбрать место server/router # ')
                if wp == 'server':
                    servers_ip = g.names['servers_buffer'] + g.names['servers_alfamed']
                    for i in servers_ip:
                        pool.apply_async(check_data_backup, (i, ))
                    pool.close()
                    pool.join()
                if wp == 'router':
                    routers_ip = g.names['routers_buffer'] + g.names['routers_alfamed']
                    for i in routers_ip:
                        res = pool.apply_async(check_data_backup, (i, ))
                    pool.close()
                    pool.join()
            elif command == 'date':
                wp = input('Выбрать место server/router # ')
                if wp == 'server':
                    check_date_rptk(g.names['servers_buffer'], g.names['servers_alfamed'])
                if wp == 'router':
                    check_date_rptk(g.names['routers_buffer'], g.names['routers_alfamed'])
            elif command == 'repl':
                print('')
                servers_ip = g.names['servers_buffer'] + g.names['servers_alfamed']
                servers_db = g.names['database_servers'] + g.names['database_alfamed']
                repl_list = [run for run in zip(servers_db, servers_ip)]
                start_check_replication(repl_list)
            elif command == 'atol':
                f = open('log_atol.csv', 'w')
                f.close()
                all_output = False
                inp_otp = input('Вывести по всем кассам - 1, только по непереданным - 0 # ')
                if int(inp_otp) == 1:
                    all_output = True
                pool = Pool(g.pool_size)
                for i in g.names['atol_buffer']:
                    pool.apply_async(atol_check, (i, all_output, ))
                pool.close()
                pool.join()
            elif command == 'copyf':
                g.clear_buffer()
                pool = Pool(g.pool_size)
                wp = input('Выбрать место server/router/server_alf/router_alf/range # ')
                start = int(input('Введите начало диапазона : аптека(1-80)/альфамед(1-10) или введите 0 если используете range # '))
                end = int(input('Введите конец диапазона : аптека(1-80)/альфамед(1-10) или введите 0 если используете range # '))
                file_path = input('Директория копируемого файла # ')
                file_name = input('Имя копируемого файла # ')
                dist_path = input(r'Директория назначения без первого слэша например: Scripts\bat # ')
                if wp == 'server':
                    g.generator_apteka(start, end)
                    for i in g.names['servers_buffer']:
                        pool.apply_async(copy_file, (file_path, file_name, dist_path, i, ))
                    pool.close()
                    pool.join()
                if wp == 'router':
                    g.generator_apteka(start, end)
                    for i in g.names['routers_buffer']:
                        pool.apply_async(copy_file, (file_path, file_name, dist_path, i,))
                    pool.close()
                    pool.join()
                if wp == 'server_alf':
                    g.generator_alfamed(start, end)
                    for i in g.names['servers_alfamed']:
                        pool.apply_async(copy_file, (file_path, file_name, dist_path, i,))
                    pool.close()
                    pool.join()
                if wp == 'router_alf':
                    g.generator_alfamed(start, end)
                    for i in g.names['routers_alfamed']:
                        pool.apply_async(copy_file, (file_path, file_name, dist_path, i,))
                    pool.close()
                    pool.join()
                if wp == 'range':
                    aptoralf = input('Ввести 1, если аптека и 0 если альфамед # ')
                    wh = input('Ввести 1, если сервер и 0 если роутер # ')
                    rg = input('Указать аптеки/альфамеды через пробел # ')
                    if int(wh) == 1:
                        if int(aptoralf) == 1:
                            g.generator_random(rg, server_apt=True, server_alf=False, router_apt=False, router_alf=False)
                        elif int(aptoralf) == 0:
                            g.generator_random(rg, server_apt=False, server_alf=True, router_apt=False, router_alf=False)
                        for i in g.names['other']:
                            pool.apply_async(copy_file, (file_path, file_name, dist_path, i, ))
                        pool.close()
                        pool.join()
                    elif int(wh) == 0:
                        if int(aptoralf) == 1:
                            g.generator_random(rg, server_apt=False, server_alf=False, router_apt=True, router_alf=False)
                        elif int(aptoralf) == 0:
                            g.generator_random(rg, server_apt=False, server_alf=False, router_apt=False, router_alf=True)
                        for i in g.names['other']:
                            pool.apply_async(copy_file, (file_path, file_name, dist_path, i, ))
                        pool.close()
                        pool.join()
            elif command == 'copyd':
                g.clear_buffer()
                pool = Pool(g.pool_size)
                wp = input('Выбрать место server/router/server_alf/router_alf/range # ')
                start = int(input('Введите начало диапазона : аптека(1-80)/альфамед(1-10) или введите 0 если используете range # '))
                end = int(input('Введите конец диапазона : аптека(1-80)/альфамед(1-10) или введите 0 если используете range # '))
                file_path = input('Директория копирования # ')
                dist_path = input(r'Директория назначения : Scripts\RPTK_release, если директория не существует, она будет создана # ')
                if wp == 'server':
                    g.generator_apteka(start, end)
                    for i in g.names['servers_buffer']:
                        pool.apply_async(copy_folder, (file_path, dist_path, i, ))
                    pool.close()
                    pool.join()
                if wp == 'router':
                    g.generator_apteka(start, end)
                    for i in g.names['routers_buffer']:
                        pool.apply_async(copy_folder, (file_path, dist_path, i, ))
                    pool.close()
                    pool.join()
                if wp == 'server_alf':
                    g.generator_alfamed(start, end)
                    for i in g.names['servers_alfamed']:
                        pool.apply_async(copy_folder, (file_path, dist_path, i, ))
                    pool.close()
                    pool.join()
                if wp == 'router_alf':
                    g.generator_alfamed(start, end)
                    for i in g.names['routers_alfamed']:
                        pool.apply_async(copy_folder, (file_path, dist_path, i, ))
                    pool.close()
                    pool.join()
                if wp == 'range':
                    aptoralf = input('Ввести 1, если аптека и 0 если альфамед # ')
                    wh = input('Ввести 1, если сервер и 0 если роутер # ')
                    rg = input('Указать аптеки/альфамеды через пробел # ')
                    if int(wh) == 1:
                        if int(aptoralf) == 1:
                            g.generator_random(rg, server_apt=True, server_alf=False, router_apt=False, router_alf=False)
                        elif int(aptoralf) == 0:
                            g.generator_random(rg, server_apt=False, server_alf=True, router_apt=False, router_alf=False)
                        for i in g.names['other']:
                            pool.apply_async(copy_folder, (file_path, dist_path, i, ))
                        pool.close()
                        pool.join()
                    elif int(wh) == 0:
                        if int(aptoralf) == 1:
                            g.generator_random(rg, server_apt=False, server_alf=False, router_apt=True, router_alf=False)
                        elif int(aptoralf) == 0:
                            g.generator_random(rg, server_apt=False, server_alf=False, router_apt=False, router_alf=True)
                        for i in g.names['other']:
                            pool.apply_async(copy_folder, (file_path, dist_path, i, ))
                        pool.close()
                        pool.join()
            elif command == 'dfile':
                g.clear_buffer()
                pool = Pool(g.pool_size)
                wp = input('Выбрать место server/router/server_alf/router_alf/range # ')
                start = int(input('Введите начало диапазона : аптека(1-80)/альфамед(101-110) или введите 0 если используете range # '))
                end = int(input('Введите конец диапазона : аптека(1-80)/альфамед(101-110) или введите 0 если используете range # '))
                dist_path = input('Директория удаляемого файла # ')
                file_name = input('Имя удаляемого файла # ')
                if wp == 'server':
                    g.generator_apteka(start, end)
                    for i in g.names['servers_buffer']:
                        pool.apply_async(delete_file, (dist_path, file_name, i, ))
                    pool.close()
                    pool.join()
                if wp == 'router':
                    g.generator_apteka(start, end)
                    for i in g.names['routers_buffer']:
                        pool.apply_async(delete_file, (dist_path, file_name, i, ))
                    pool.close()
                    pool.join()
                if wp == 'server_alf':
                    g.generator_alfamed(start, end)
                    for i in g.names['servers_alfamed']:
                        pool.apply_async(delete_file, (dist_path, file_name, i, ))
                    pool.close()
                    pool.join()
                if wp == 'router_alf':
                    g.generator_alfamed(start, end)
                    for i in g.names['routers_alfamed']:
                        pool.apply_async(delete_file, (dist_path, file_name, i, ))
                    pool.close()
                    pool.join()
                if wp == 'range':
                    aptoralf = input('Ввести 1, если аптека и 0 если альфамед # ')
                    wh = input('Ввести 1, если сервер и 0 если роутер # ')
                    rg = input('Указать аптеки/альфамеды через пробел # ')
                    if int(wh) == 1:
                        if int(aptoralf) == 1:
                            g.generator_random(rg, server_apt=True, server_alf=False, router_apt=False, router_alf=False)
                        elif int(aptoralf) == 0:
                            g.generator_random(rg, server_apt=False, server_alf=True, router_apt=False, router_alf=False)
                        for i in g.names['other']:
                            pool.apply_async(delete_file, (dist_path, file_name, i, ))
                        pool.close()
                        pool.join()
                    elif int(wh) == 0:
                        if int(aptoralf) == 1:
                            g.generator_random(rg, server_apt=False, server_alf=False, router_apt=True, router_alf=False)
                        elif int(aptoralf) == 0:
                            g.generator_random(rg, server_apt=False, server_alf=False, router_apt=False, router_alf=True)
                        for i in g.names['other']:
                            pool.apply_async(delete_file, (dist_path, file_name, i, ))
                        pool.close()
                        pool.join()
            elif command == 'ddir':
                g.clear_buffer()
                pool = Pool(g.pool_size)
                wp = input('Выбрать место server/router/server_alf/router_alf/range # ')
                start = int(input('Введите начало диапазона : аптека(1-80)/альфамед(101-110) или введите 0 если используете range # '))
                end = int(input('Введите конец диапазона : аптека(1-80)/альфамед(101-110) или введите 0 если используете range # '))
                dist_path = input(r'Директория которую надо очистить : Scripts\auto # ')
                if wp == 'server':
                    g.generator_apteka(start, end)
                    for i in g.names['servers_buffer']:
                        pool.apply_async(delete_all_in_folder, (dist_path, i, ))
                    pool.close()
                    pool.join()
                if wp == 'router':
                    g.generator_apteka(start, end)
                    for i in g.names['routers_buffer']:
                        pool.apply_async(delete_all_in_folder, (dist_path, i, ))
                    pool.close()
                    pool.join()
                if wp == 'server_alf':
                    g.generator_alfamed(start, end)
                    for i in g.names['servers_alfamed']:
                        pool.apply_async(delete_all_in_folder, (dist_path, i, ))
                    pool.close()
                    pool.join()
                if wp == 'router_alf':
                    g.generator_alfamed(start, end)
                    for i in g.names['routers_alfamed']:
                        pool.apply_async(delete_all_in_folder, (dist_path, i, ))
                    pool.close()
                    pool.join()
                if wp == 'range':
                    aptoralf = input('Ввести 1, если аптека и 0 если альфамед # ')
                    wh = input('Ввести 1, если сервер и 0 если роутер # ')
                    rg = input('Указать аптеки/альфамеды через пробел # ')
                    if int(wh) == 1:
                        if int(aptoralf) == 1:
                            g.generator_random(rg, server_apt=True, server_alf=False, router_apt=False, router_alf=False)
                        elif int(aptoralf) == 0:
                            g.generator_random(rg, server_apt=False, server_alf=True, router_apt=False, router_alf=False)
                        for i in g.names['other']:
                            pool.apply_async(delete_all_in_folder, (dist_path, i, ))
                        pool.close()
                        pool.join()
                    elif int(wh) == 0:
                        if int(aptoralf) == 1:
                            g.generator_random(rg, server_apt=False, server_alf=False, router_apt=True, router_alf=False)
                        elif int(aptoralf) == 0:
                            g.generator_random(rg, server_apt=False, server_alf=False, router_apt=False, router_alf=True)
                        for i in g.names['other']:
                            pool.apply_async(delete_all_in_folder, (dist_path, i, ))
                        pool.close()
                        pool.join()
            else:
                print(Fore.RED, 'Команда не найдена')
    except KeyboardInterrupt:
        print('\n')
        print(Fore.CYAN, 'Успешный выход !')
        exit()
    except Exception as error:
        print(Fore.RED, error)


if __name__ == '__main__':
    g = Generator()
    lock = Lock()
    print_intro()
    start()
