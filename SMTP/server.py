import socket
import socketserver
import pymysql
import base64

db = pymysql.connect(host='localhost',
                     user='root',
                     password='shuixirui',
                     database='mscdb')
cursor = db.cursor()


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
        return "".join(total_data)

    def check_ip_list(self):  # 获取域名解析出的IP列表
        ip_list = []

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

    def check_user(self):
        sql = "SELECT * FROM users WHERE username = '" + self.client_name + "'"

        try:
            cursor.execute(sql)
            results = cursor.fetchall()
            for row in results:
                if row[1] == self.client_pass:
                    self.client_type = 2
                    break;

        except Exception as e:
            print(str(e))
            pass

    def save_mail(self, receiver_addr):
        sql = "INSERT INTO MAILS(sender,receiver,create_time,content) VALUES ('" + self.sender_addr + "', '" + receiver_addr + "', now(), '" + self.content + "')"
        try:
            cursor.execute(sql)
            db.commit()
        except:
            # 如果发生错误则回滚
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

    def handle(self):

        self.server_domain="msc.com"
        self.request.sendall(b'220 welcome ,i"m here\r\n')
        self.client_ip = self.client_address[0]
        error_msg = "502 Invalid input from " + self.client_ip + " to msc.com\r\n"

        self.process_turn = 0
        self.client_type = 0

        while True:
            self.data = self.recv_endswith("\r\n").strip()
            print(self.data[0:4])
            if self.data.upper() == "QUIT":
                self.request.sendall(b'221 bye\r\n')
                break

            elif self.data[0:4].upper() == "EHLO":
                self.domain = self.data[5:]

                self.check_ip_list()

                if self.client_type == 1:
                    self.request.sendall('''250-imagine.msc.com
                                            250-PIPELINING
                                            250-SIZE 1024
                                            250-STARTTLS
                                            250-AUTH LOGIN PLAIN XOAUTH XOAUTH2
                                            250-AUTH=LOGIN
                                            250-MAILCOMPRESS
                                            250 8BITMIME\r\n.\r\n''')
                else:
                    self.request.sendall('''250-imagine.msc.com
                                            250-PIPELINING
                                            250-SIZE 1024
                                            250-STARTTLS
                                            250-AUTH LOGIN PLAIN XOAUTH XOAUTH2
                                            250-AUTH=LOGIN
                                            250-MAILCOMPRESS
                                            250 8BITMIME\r\n.\r\n''')

            elif self.data.upper() == "AUTH LOGIN":

                self.request.sendall(b'334 VXNlcm5hbWU6\r\n')
                self.data = self.recv_endswith("\r\n").strip()
                self.client_name = base64.b64decode(self.data).decode("utf-8")

                self.request.sendall(b'334 UGFzc3dvcmQ6\r\n')
                self.data = self.recv_endswith("\r\n").strip()
                self.client_pass = base64.b64decode(self.data).decode("utf-8")

                self.check_user()

                if self.client_type == 2:
                    self.request.sendall(b'235 Authentication successful\r\n')
                else:
                    self.request.sendall(b'502 unable to fetch data\r\n')

            elif (self.data[0:11]+self.data[-1]).upper() == "MAIL FROM:<>":
                if self.client_type != 0:
                    self.sender_addr = self.data[11:-1]
                    self.receiver_list=[]
                    self.request.sendall(b'250 OK\r\n')
                    self.process_turn = 1
                else:
                    self.request.sendall(b'503 Send command HELO/EHLO first.\r\n')

            elif (self.data[0:9]+self.data[-1]).upper() == "RCPT TO:<>":
                if self.process_turn >= 1:
                    self.receiver_list.append(self.data[9:-1])
                    self.request.sendall(b'250 OK\r\n')
                    self.process_turn = 2
                else:
                    self.request.sendall(b'503 Send command mailfrom first.\r\n')

            elif self.data.upper() == "DATA":
                if self.process_turn == 2:
                    self.request.sendall(b'354 End data with <CR><LF>.<CR><LF>.\r\n')
                    self.content = self.recv_endswith("\r\n.\r\n").strip()
                    for rec in self.receiver_list:
                        if rec.endswith(self.server_domain):
                            self.save_mail(rec)
                        else:
                            self.send_mail(rec)
                    self.request.sendall(b'250 OK\r\n')
                    self.process_turn = 0
                else:
                    self.request.sendall(b'503 Send command rcptto first.\r\n')

            else:
                self.request.sendall(error_msg.encode())


if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 8000
    server = socketserver.ThreadingTCPServer((HOST, PORT), Myserver)
    server.serve_forever()
