import socket
import socketserver
import pymysql
import base64
import hashlib
import cryptography

db = pymysql.connect(host='localhost',
                     user='root',
                     password='shuixirui',
                     database='mscdb')
cursor = db.cursor()

sql_query = "SELECT * FROM users WHERE username = %s"
sql_save = "INSERT INTO MAILS(uid,sender,receiver,create_time,content) VALUES (UUID(), %s, %s, now(), %s)"


class Myserver(socketserver.BaseRequestHandler):

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
        try:
            addrs = socket.getaddrinfo(self.domain, None)

            for item in addrs:
                if item[4][0] not in ip_list:
                    ip_list.append(item[4][0])
        except Exception as e:
            print(str(e))
            pass

        for ip in ip_list:
            if ip == self.client_ip:
                self.client_type = 1

    def check_existence(self, user_addr):
        if user_addr.endswith(self.server_domain):
            data_tuple = (user_addr,)
            try:
                cursor.execute(sql_query, data_tuple)
                results = cursor.fetchall()
                for row in results:
                    return True

            except Exception as e:
                print(str(e))
                return False
                pass
            return False
        else:
            return True

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

    def save_mail(self, receiver_addr):
        data_tuple=(self.sender_addr, receiver_addr, self.content)
        try:
            cursor.execute(sql_save,data_tuple)
            db.commit()
            self.request.sendall(b'250 queued as\r\n')
        except Exception as e:
            print(str(e))
            # 如果发生错误则回滚
            self.request.sendall(b'502 unable to fetch data\r\n')
            db.rollback()
            pass

    def send_mail(self, receiver_addr):
        tcpclient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpclient.connect((self.client_ip, 25))
        ret = tcpclient.recv(1024)

        data = "EHLO " + self.server_domain + "\r\n"
        tcpclient.send(data.encode('utf-8'))
        ret = tcpclient.recv(1024)

        data = "MAIL FROM:<" + self.sender_addr + ">\r\n"
        tcpclient.send(data.encode('utf-8'))
        ret = tcpclient.recv(1024)

        data = "RCPT TO:<" + receiver_addr + ">\r\n"
        tcpclient.send(data.encode('utf-8'))
        ret = tcpclient.recv(1024)

        data = "DATA\r\n"
        tcpclient.send(data.encode('utf-8'))
        ret = tcpclient.recv(1024)

        data = self.content + "\r\n.\r\n"
        tcpclient.send(data.encode('utf-8'))
        ret = tcpclient.recv(1024)

        data = "QUIT\r\n"
        tcpclient.send(data.encode('utf-8'))
        ret = tcpclient.recv(1024)

        tcpclient.close()
        self.request.sendall(b'250 queued as\r\n')

    def handle(self):

        self.server_domain = "msc.com"
        self.request.sendall(b'220 welcome ,i"m here\r\n')
        self.client_ip = self.client_address[0]
        error_msg = "502 Invalid input from " + self.client_ip + " to msc.com\r\n"

        self.process_turn = 0
        self.client_type = 2

        while True:
            self.data = self.recv_endswith("\r\n").strip()
            if self.data.upper() == "QUIT":
                self.request.sendall(b'221 bye\r\n')
                break

            elif self.data[0:4].upper() == "EHLO":
                self.domain = self.data[5:]

                self.check_ip_list()

                self.request.sendall(b'''250-msc.com
250-SIZE 73400320
250-AUTH LOGIN 
250-AUTH=LOGIN
250 8BITMIME\r\n.\r\n''')

            elif self.data.upper() == "AUTH LOGIN":

                self.request.sendall(b'334 VXNlcm5hbWU6\r\n')
                self.data = self.recv_endswith("\r\n").strip()
                self.client_name = base64.b64decode(self.data).decode("utf-8")

                self.request.sendall(b'334 UGFzc3dvcmQ6\r\n')
                self.data = self.recv_endswith("\r\n").strip()
                self.client_pass = hashlib.md5(base64.b64decode(self.data)).hexdigest()

                self.check_user()

                if self.client_type == 2:
                    self.request.sendall(b'235 Authentication successful\r\n')
                else:
                    self.request.sendall(b'502 unable to fetch data\r\n')

            elif (self.data[0:11] + self.data[-1]).upper() == "MAIL FROM:<>":
                if self.client_type != 0:
                    self.sender_addr = self.data[11:-1]
                    self.receiver_list = []
                    self.request.sendall(b'250 OK\r\n')
                    self.process_turn = 1
                else:
                    self.request.sendall(b'503 Send command HELO/EHLO first.\r\n')

            elif (self.data[0:9] + self.data[-1]).upper() == "RCPT TO:<>":
                if self.process_turn >= 1:
                    print(self.data[9:-1])
                    print(self.data[9:-2])
                    if self.check_existence(self.data[9:-1]):
                        self.receiver_list.append(self.data[9:-1])
                        self.request.sendall(b'250 OK\r\n')
                        self.process_turn = 2
                    else:
                        self.request.sendall(b'502 unable to fetch data\r\n')
                else:
                    self.request.sendall(b'503 Send command mailfrom first.\r\n')

            elif self.data.upper() == "DATA":
                if self.process_turn == 2:
                    self.request.sendall(b'354 End data with <CR><LF>.<CR><LF>.\r\n')
                    self.content = self.recv_endswith("\r\n.\r\n").strip()
                    if len(self.content) <= 73400320:
                        for rec in self.receiver_list:
                            if rec.endswith(self.server_domain):
                                self.save_mail(rec)
                            else:
                                self.send_mail(rec)
                        self.process_turn = 0
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
