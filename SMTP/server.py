import socket
import socketserver
import pymysql
import base64
import hashlib
import time
import re
import cryptography

db = pymysql.connect(host='localhost',
                     user='root',
                     password='shuixirui',
                     database='mscdb')
cursor = db.cursor()

sql_query = "SELECT * FROM users WHERE username = %s"
sql_save = "INSERT INTO MAILS(uid,sender,receiver,create_time,content) VALUES (UUID(), %s, %s, now(), %s)"

re_email = re.compile(r'^[a-zA-Z\.]+@[a-zA-Z0-9]+\.[a-zA-Z]{3}$')


class Myserver(socketserver.BaseRequestHandler):

    def get_time(self):
        ticks = time.time()
        localtime = time.localtime(time.time())
        return time.strftime("%a ,%d %b %Y %H:%M:%S %z", time.localtime())

    def is_base64_code(self, s):
        '''Check s is Base64.b64encode'''
        if not isinstance(s, str) or not s:
            return 0

        _base64_code = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I',
                        'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R',
                        'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a',
                        'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
                        'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's',
                        't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1',
                        '2', '3', '4', '5', '6', '7', '8', '9', '+',
                        '/', '=']

        # Check base64 OR codeCheck % 4
        code_fail = [i for i in s if i not in _base64_code]
        if code_fail or len(s) % 4 != 0:
            return 1
        return 2

    def recv_endswith(self, End):
        total_data = []
        data = ''
        while True:
            data = self.request.recv(1024).decode("utf-8")
            if End in data:
                total_data.append(data[:data.find(End)])
                break
            total_data.append(data)
            if len(total_data) > 1:
                # check if end_of_data was split
                last_pair = total_data[-2] + total_data[-1]
                if End in last_pair:
                    total_data[-2] = last_pair[:last_pair.find(End)]
                    total_data.pop()
                    break
        return ("".join(total_data)).replace(End, '')

    def check_ip_list(self):  # 获取域名解析出的IP列表
        ip_list = []
        self.domain.encode("utf-8")
        if len(self.domain) <= 1:
            self.request.sendall(b'502 please enter domain\r\n')
            return

        try:
            addrs = socket.getaddrinfo(self.domain, None)
            for item in addrs:
                if item[4][0] not in ip_list:
                    ip_list.append(item[4][0])
        except Exception as e:
            print(str(e))
            self.request.sendall(b'502 Invalid domain,getaddrinfo failed\r\n')
            return

        self.request.sendall(b'''250-msc.com
250-SIZE 73400320
250-AUTH LOGIN 
250-AUTH=LOGIN
250 8BITMIME\r\n.\r\n''')

        for ip in ip_list:
            if ip == self.client_ip:
                self.client_type = 1
                return

    def check_existence(self, user_addr):
        if user_addr.endswith(self.server_domain):
            user_addr=user_addr.replace("@msc.com", "")
            data_tuple = (user_addr,)
            try:
                cursor.execute(sql_query, data_tuple)
                results = cursor.fetchall()
                for row in results:
                    self.request.sendall(b'250 OK\r\n')
                    return True

            except Exception as e:
                print(str(e))
                self.request.sendall(b'503 server error,please wait and try latter\r\n')
                return False
                pass
            self.request.sendall(b'503 the inside user is not exist\r\n')
            return False
        else:
            if re_email.match(user_addr):
                self.request.sendall(b'250 OK\r\n')
                return True
            else:
                self.request.sendall(b'503 the receiver is invalid\r\n')
                return False

    def check_user(self):
        data_tuple = (self.client_name,)
        try:
            cursor.execute(sql_query, data_tuple)
            results = cursor.fetchall()
            for row in results:
                if row[1] == self.client_pass:
                    self.client_type = 2

        except Exception as e:
            print(str(e))
            pass

    def create_mail(self, sender, cont):
        From = "From: " + self.server_user + "\n"
        To = "To: " + sender + "\n"
        Date = "Date: " + self.get_time() + "\n"
        Subject = "Subject: =?utf-8?b?5a+55LiN6LW377yM5oKo55qE6YKu5Lu25Y+R6YCB5aSx6LSl?=\n"
        Setting = "Content-Type: text/plain; charset=utf-8\n"
        return From + To + Date + Subject + Setting + cont

    def save_mail(self, sender, rec, cont):
        cont = "Received : from " + self.domain \
               + " by " + self.server_domain \
               + " for <" + rec \
               + "> ; " + self.get_time() \
               + "\n" + cont
        data_tuple = (sender, rec, cont)
        try:
            cursor.execute(sql_save, data_tuple)
            db.commit()
        except Exception as e:
            print(str(e))
            # 如果发生错误则回滚
            db.rollback()
            pass

    def send_mail(self, sender, rec, cont):
        cont = "Received : from " + self.domain \
               + " by " + self.server_domain \
               + " for <" + rec \
               + "> ; " + self.get_time() \
               + "\n" + cont

        tcpclient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpclient.connect((self.client_ip, 25))
        ret = self.recv_endswith("\r\n").strip()

        dat = "EHLO " + self.server_domain + "\r\n"
        tcpclient.send(dat.encode('utf-8'))
        ret = self.recv_endswith("\r\n.\r\n").strip()
        if ret[0] == '5':
            self.save_mail(self.server_user, sender, self.create_mail(sender, ret))
            return

        dat = "MAIL FROM:<" + sender + ">\r\n"
        tcpclient.send(dat.encode('utf-8'))
        ret = self.recv_endswith("\r\n").strip()
        if ret[0] == '5':
            self.save_mail(self.server_user, sender, self.create_mail(sender, ret))
            return

        dat = "RCPT TO:<" + rec + ">\r\n"
        tcpclient.send(dat.encode('utf-8'))
        ret = self.recv_endswith("\r\n").strip()
        if ret[0] == '5':
            self.save_mail(self.server_user, sender, self.create_mail(sender, ret))
            return

        dat = "DATA\r\n"
        tcpclient.send(dat.encode('utf-8'))
        ret = self.recv_endswith("\r\n").strip()
        if ret[0] == '5':
            self.save_mail(self.server_user, sender, self.create_mail(sender, ret))
            return

        dat = cont + "\r\n.\r\n"
        tcpclient.send(dat.encode('utf-8'))
        ret = self.recv_endswith("\r\n").strip()
        if ret[0] == '5':
            self.save_mail(self.server_user, sender, self.create_mail(sender, ret))
            return

        dat = "QUIT\r\n"
        tcpclient.send(dat.encode('utf-8'))
        ret = self.recv_endswith("\r\n").strip()
        if ret[0] == '5':
            self.save_mail(self.server_user, sender, self.create_mail(sender, ret))
            return

        tcpclient.close()

    def solve_work(self, work):
        for rec in work[1]:
            if rec.endswith(self.server_domain):
                self.save_mail(work[0], rec, work[2])
            else:
                self.send_mail(work[0], rec, work[2])

    def handle(self):

        self.domain = ""
        self.server_domain = "msc.com"
        self.server_user = "manager@msc.com"
        self.request.sendall(b'220 welcome ,i"m here\r\n')
        self.client_ip = self.client_address[0]
        error_msg = "502 Invalid input from " + self.client_ip + " to msc.com\r\n"
        noop_msg = "250 OK from " + self.client_ip + "to msc.com\r\n"

        self.process_turn = 0
        self.client_type = 0

        self.total_works = []
        self.one_work = []

        while True:
            self.data = self.recv_endswith("\r\n").strip()
            if self.data.upper() == "QUIT":
                for work in self.total_works:
                    self.solve_work(work)
                self.request.sendall(b'221 Bye\r\n')
                return

            elif self.data.upper() == "NOOP":
                self.request.sendall(noop_msg.encode())

            elif self.data.upper() == "RSET":
                self.total_works = ()
                self.process_turn = 0
                self.client_type = 0
                self.request.sendall(b'250 OK\r\n')

            elif self.data[0:4].upper() == "EHLO":
                self.domain = self.data[5:]
                self.check_ip_list()

            elif self.data.upper() == "AUTH LOGIN":

                self.request.sendall(b'334 VXNlcm5hbWU6\r\n')
                self.client_name = self.recv_endswith("\r\n").strip()
                self.request.sendall(b'334 UGFzc3dvcmQ6\r\n')
                self.client_pass = self.recv_endswith("\r\n").strip()

                if self.is_base64_code(self.client_name) == 0 or self.is_base64_code(self.client_pass) == 0:
                    self.request.sendall(b'503 please keep the information not none\r\n')
                elif self.is_base64_code(self.client_name) == 1 or self.is_base64_code(self.client_pass) == 1:
                    self.request.sendall(b'503 please keep the information is base64 code\r\n')
                else:
                    self.client_name = base64.b64decode(self.client_name).decode("utf-8")
                    self.client_name = self.client_name.replace("@msc.com", "")
                    self.client_pass = hashlib.md5(base64.b64decode(self.client_pass)).hexdigest()

                    self.check_user()

                    if self.client_type == 2:
                        self.request.sendall(b'235 Authentication successful\r\n')
                    else:
                        self.request.sendall(b'535 Login Fail. Please enter right information to login.\r\n')

            elif (self.data[0:11] + self.data[-1]).upper() == "MAIL FROM:<>":
                if self.client_type != 0:
                    self.one_work = []
                    self.sender_addr = self.data[11:-1]
                    self.receiver_list = []
                    self.request.sendall(b'250 OK\r\n')
                    self.process_turn = 1
                else:
                    self.request.sendall(b'503 Send command HELO/EHLO first.\r\n')

            elif (self.data[0:9] + self.data[-1]).upper() == "RCPT TO:<>":
                if self.process_turn >= 1:
                    if self.check_existence(self.data[9:-1]):
                        self.receiver_list.append(self.data[9:-1])
                        self.process_turn = 2
                else:
                    self.request.sendall(b'503 Send command mailfrom first.\r\n')

            elif self.data.upper() == "DATA":
                if self.process_turn == 2:
                    self.request.sendall(b'354 End data with <CR><LF>.<CR><LF>.\r\n')
                    self.content = self.recv_endswith("\r\n.\r\n").strip()
                    if len(self.content) <= 73400320:
                        self.one_work.append(self.sender_addr)
                        self.one_work.append(self.receiver_list)
                        self.one_work.append(self.content)
                        self.total_works.append(self.one_work)
                        self.process_turn = 0
                        self.request.sendall(b'250 OK:queued as.\r\n')
                    else:
                        self.request.sendall(b'503 Content is too long.\r\n')
                else:
                    self.request.sendall(b'503 Send command rcptto first.\r\n')

            else:
                self.request.sendall(error_msg.encode())


if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 25
    server = socketserver.ThreadingTCPServer((HOST, PORT), Myserver)
    server.serve_forever()
