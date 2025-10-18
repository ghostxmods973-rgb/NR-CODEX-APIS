from flask import Flask, request, jsonify
from SpamReqInvApiMain import *
from SpamReqInvApiSetting import *
import threading
import time
import socket
import json
import base64
import requests
from datetime import datetime
import jwt
from google.protobuf.timestamp_pb2 import Timestamp
import errno
import select
import atexit
import os
import signal
import sys
import psutil
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
clients = {}
shutting_down = False

shared_0500_info = {
    'got': False,
    'idT': None,
    'squad': None,
    'AutH': None
}

MASTER_ACCOUNT_ID = '3901729512'  # عدل حسب حسابك الرئيسي

def AuTo_ResTartinG():
    while not shutting_down:
        time.sleep(3 * 60)
        print('\n - AuTo ResTartinG The BoT ... ! ')
        p = psutil.Process(os.getpid())
        for handler in p.open_files():
            try:
                os.close(handler.fd)
            except Exception as e:
                print(f" - Error CLose Files : {e}")
        for conn in p.connections():
            try:
                if hasattr(conn, 'fd'):
                    os.close(conn.fd)
            except Exception as e:
                print(f" - Error CLose Connection : {e}")
        python = sys.executable
        os.execl(python, python, *sys.argv)

def ResTarT_BoT():
    print('\n - ResTartinG The BoT ... ! ')
    p = psutil.Process(os.getpid())
    for handler in p.open_files():
        try:
            os.close(handler.fd)
        except Exception:
            pass           
    for conn in p.connections():
        try:
            conn.close()
        except Exception:
            pass
    python = sys.executable
    os.execl(python, python, *sys.argv)

class TcpBotConnectMain:
    def __init__(self, account_id, password):
        self.account_id = account_id
        self.password = password
        self.key = None
        self.iv = None
        self.socket_client = None
        self.clientsocket = None
        self.running = False
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        self.AutH = None
        self.DaTa2 = None
    
    def run(self):
        if shutting_down:
            return
            
        # بدء إعادة التشغيل التلقائي لوحدة العميل مرة واحدة
        if not hasattr(self, "auto_restart_thread_started"):
            t = threading.Thread(target=AuTo_ResTartinG, daemon=True)
            t.start()
            self.auto_restart_thread_started = True
        
        self.running = True
        self.connection_attempts = 0
        
        while self.running and not shutting_down and self.connection_attempts < self.max_connection_attempts:
            try:
                self.connection_attempts += 1
                print(f"[{self.account_id}] محاولة الاتصال {self.connection_attempts}/{self.max_connection_attempts}")
                self.get_tok()
                break
            except Exception as e:
                print(f"[{self.account_id}] Error in run: {e}")
                if self.connection_attempts >= self.max_connection_attempts:
                    print(f"[{self.account_id}] وصل للحد الأقصى لمحاولات الاتصال. التوقف.")
                    self.stop()
                    break
                print(f"[{self.account_id}] إعادة المحاولة بعد 5 ثواني...")
                time.sleep(5)
    
    def stop(self):
        self.running = False
        try:
            if self.clientsocket:
                self.clientsocket.close()
        except:
            pass
        try:
            if self.socket_client:
                self.socket_client.close()
        except:
            pass
        print(f"[{self.account_id}] Client stopped")
    
    def restart(self, delay=5):
        if shutting_down:
            return
            
        print(f"[{self.account_id}] Restarting client in {delay} seconds...")
        time.sleep(delay)
        self.run()
    
    def is_socket_connected(self, sock):
        try:
            if sock is None:
                return False
            writable = select.select([], [sock], [], 0.1)[1]
            if sock in writable:
                sock.send(b'')
                return True
            return False
        except (OSError, socket.error) as e:
            if e.errno == errno.EBADF:
                print(f"[{self.account_id}] Socket bad file descriptor")
            return False
        except Exception as e:
            print(f"[{self.account_id}] Socket check error: {e}")
            return False
    
    def ensure_connection(self):
        if not self.is_socket_connected(self.socket_client) and self.running:
            print(f"[{self.account_id}] Attempting to reconnect")
            self.restart(delay=2)
            return False
        return True
    
    def sockf1(self, tok, online_ip, online_port, packet, key, iv):
        while self.running and not shutting_down:
            try:
                self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket_client.settimeout(30)
                self.socket_client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                
                online_port = int(online_port)
                print(f"[{self.account_id}] Connecting to {online_ip}:{online_port}...")
                self.socket_client.connect((online_ip, online_port))
                print(f"[{self.account_id}] Connected to {online_ip}:{online_port}")
                self.socket_client.send(bytes.fromhex(tok))
                print(f"[{self.account_id}] Token sent successfully")
                
                while self.running and not shutting_down and self.is_socket_connected(self.socket_client):
                    try:
                        readable, _, _ = select.select([self.socket_client], [], [], 1.0)
                        if self.socket_client in readable:
                            self.DaTa2 = self.socket_client.recv(99999)
                            if not self.DaTa2:
                                print(f"[{self.account_id}] Server closed connection gracefully")
                                break

                            # التحقق من باك 0500
                            if '0500' in self.DaTa2.hex()[0:4] and len(self.DaTa2.hex()) > 30:
                                try:
                                    self.packet = json.loads(DeCode_PackEt(f'08{self.DaTa2.hex().split("08", 1)[1]}'))
                                    self.AutH = self.packet['5']['data']['7']['data']
                                    print(f"[{self.account_id}] 0500 packet received, AutH={self.AutH}")

                                    # إذا كان Master احفظ البيانات للعامة
                                    if self.account_id == MASTER_ACCOUNT_ID:
                                        shared_0500_info['got'] = True
                                        shared_0500_info['idT'] = self.packet['5']['data']['1']['data']
                                        shared_0500_info['squad'] = self.packet['5']['data']['31']['data']
                                        shared_0500_info['AutH'] = self.AutH
                                        print(f"[{self.account_id}] Master saved 0500 info")

                                    # إرسال Ghost packet تلقائيًا لكل الحسابات بعد الحصول على 0500
                                    elif shared_0500_info['got']:
                                        idT = shared_0500_info['idT']
                                        sq = shared_0500_info['squad']
                                        for _ in range(3):
                                            self.socket_client.send(GenJoinSquadsPacket(idT, key, iv))
                                            time.sleep(0.5)
                                            self.socket_client.send(ExiT('000000', key, iv))
                                            self.socket_client.send(ghost_pakcet(idT, "insta:kha_led_mhd", sq, key, iv))
                                            time.sleep(0.5)

                                except Exception as parse_err:
                                    print(f"[{self.account_id}] Error parsing 0500: {parse_err}")
                                
                    except socket.timeout:
                        continue
                    except (OSError, socket.error) as e:
                        if e.errno == errno.EBADF:
                            print(f"[{self.account_id}] Bad file descriptor, reconnecting...")
                            break
                        else:
                            print(f"[{self.account_id}] Socket error: {e}. Reconnecting...")
                            break
                    except Exception as e:
                        print(f"[{self.account_id}] Unexpected error: {e}. Reconnecting...")
                        break
                        
            except socket.timeout:
                print(f"[{self.account_id}] Connection timeout, retrying...")
            except (OSError, socket.error) as e:
                if e.errno == errno.EBADF:
                    print(f"[{self.account_id}] Bad file descriptor during connection")
                else:
                    print(f"[{self.account_id}] Connection error: {e}")
            except Exception as e:
                print(f"[{self.account_id}] Unexpected error: {e}")
    def connect(self, tok, packet, key, iv, whisper_ip, whisper_port, online_ip, online_port):
        while self.running and not shutting_down:
            try:
                self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.clientsocket.settimeout(None)
                self.clientsocket.connect((whisper_ip, int(whisper_port)))
                print(f"[{self.account_id}] Connected to {whisper_ip}:{whisper_port}")
                self.clientsocket.send(bytes.fromhex(tok))
                self.data = self.clientsocket.recv(1024)
                self.clientsocket.send(get_packet2(self.key, self.iv))

                thread = threading.Thread(
                    target=self.sockf1,
                    args=(tok, online_ip, online_port, "anything", key, iv)
                )
                thread.daemon = True
                thread.start()
                
                while self.running and not shutting_down:
                    dataS = self.clientsocket.recv(1024)
                    if not dataS:
                        break
            except Exception as e:
                if not shutting_down:
                    print(f"[{self.account_id}] Error in connect: {e}. Retrying in 3 seconds...")
                    time.sleep(3)
            finally:
                if self.clientsocket:
                    try:
                        self.clientsocket.close()
                    except:
                        pass
                
                if self.running and not shutting_down:
                    time.sleep(2)
    
    def parse_my_message(self, serialized_data):
        MajorLogRes = MajorLoginRes() 
        MajorLogRes.ParseFromString(serialized_data)
        timestamp = MajorLogRes.kts
        key = MajorLogRes.ak
        iv = MajorLogRes.aiv
        BASE64_TOKEN = MajorLogRes.token
        timestamp_obj = Timestamp()
        timestamp_obj.FromNanoseconds(timestamp)
        timestamp_seconds = timestamp_obj.seconds
        timestamp_nanos = timestamp_obj.nanos
        combined_timestamp = timestamp_seconds * 1_000_000_000 + timestamp_nanos
        return combined_timestamp, key, iv, BASE64_TOKEN
    
    def GET_PAYLOAD_BY_DATA(self, JWT_TOKEN, NEW_ACCESS_TOKEN, date):
        token_payload_base64 = JWT_TOKEN.split('.')[1]
        token_payload_base64 += '=' * ((4 - len(token_payload_base64) % 4) % 4)
        decoded_payload = base64.urlsafe_b64decode(token_payload_base64).decode('utf-8')
        decoded_payload = json.loads(decoded_payload)
        NEW_EXTERNAL_ID = decoded_payload['external_id']
        SIGNATURE_MD5 = decoded_payload['signature_md5']
        now = datetime.now()
        now = str(now)[:len(str(now))-7]
        formatted_time = date
        payload = bytes.fromhex(Payload1A13)
        payload = payload.replace(b"2025-08-02 17:15:04", str(now).encode())
        payload = payload.replace(b"10e299be9f8199bd50f8c52bbae4695bc1935563ba17d3859c97237bd45cb428", NEW_ACCESS_TOKEN.encode("UTF-8"))
        payload = payload.replace(b"b70245b92be827af56d8932346f351f2", NEW_EXTERNAL_ID.encode("UTF-8"))
        payload = payload.replace(b"7428b253defc164018c604a1ebbfebdf", SIGNATURE_MD5.encode("UTF-8"))
        PAYLOAD = payload.hex()
        PAYLOAD = encrypt_api(PAYLOAD)
        PAYLOAD = bytes.fromhex(PAYLOAD)
        whisper_ip, whisper_port, online_ip, online_port = self.GET_LOGIN_DATA(JWT_TOKEN, PAYLOAD)
        return whisper_ip, whisper_port, online_ip, online_port
    
    def GET_LOGIN_DATA(self, JWT_TOKEN, PAYLOAD):
        url = GetLoginDataRegionMena
        headers = {
            'Expect': '100-continue',
            'Authorization': f'Bearer {JWT_TOKEN}',
            'X-Unity-Version': '2018.4.11f1',
            'X-GA': 'v1 1',
            'ReleaseVersion': FreeFireVersion,
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)',
            'Host': 'clientbp.common.ggbluefox.com',
            'Connection': 'close',
            'Accept-Encoding': 'gzip, deflate, br',
        }
        
        max_retries = 3
        attempt = 0
        while attempt < max_retries and not shutting_down:
            try:
                response = requests.post(url, headers=headers, data=PAYLOAD, verify=False)
                response.raise_for_status()
                x = response.content.hex()
                json_result = get_available_room(x)
                parsed_data = json.loads(json_result)
                whisper_address = parsed_data['32']['data']
                online_address = parsed_data['14']['data']
                online_ip = online_address[:len(online_address) - 6]
                whisper_ip = whisper_address[:len(whisper_address) - 6]
                online_port = int(online_address[len(online_address) - 5:])
                whisper_port = int(whisper_address[len(whisper_address) - 5:])
                return whisper_ip, whisper_port, online_ip, online_port
            except requests.RequestException as e:
                print(f"[{self.account_id}] Request failed: {e}. Attempt {attempt + 1} of {max_retries}. Retrying...")
                attempt += 1
                time.sleep(2)
        print(f"[{self.account_id}] Failed to get login data after multiple attempts.")
        return None, None, None, None
    
    def guest_token(self, uid, password):
        url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        headers = {"Host": "100067.connect.garena.com","User-Agent": "GarenaMSDK/4.0.19P4(G011A ;Android 10;en;EN;)","Content-Type": 'application/x-www-form-urlencoded',"Accept-Encoding": "gzip, deflate, br","Connection": "close",}
        data = {"uid": f"{uid}","password": f"{password}","response_type": "token","client_type": "2","client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3","client_id": "100067",}
        response = requests.post(url, headers=headers, data=data)
        data = response.json()
        NEW_ACCESS_TOKEN = data['access_token']
        NEW_OPEN_ID = data['open_id']
        OLD_ACCESS_TOKEN = "10e299be9f8199bd50f8c52bbae4695bc1935563ba17d3859c97237bd45cb428"
        OLD_OPEN_ID = "b70245b92be827af56d8932346f351f2"
        time.sleep(0.2)
        data = self.TOKEN_MAKER(OLD_ACCESS_TOKEN, NEW_ACCESS_TOKEN, OLD_OPEN_ID, NEW_OPEN_ID, uid)
        return data
        
    def TOKEN_MAKER(self, OLD_ACCESS_TOKEN, NEW_ACCESS_TOKEN, OLD_OPEN_ID, NEW_OPEN_ID, id):
        headers = {
            'X-Unity-Version': '2018.4.11f1',
            'ReleaseVersion': FreeFireVersion,
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-GA': 'v1 1',
            'Content-Length': '928',
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
            'Host': 'loginbp.ggblueshark.com',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip'
        }
        data = bytes.fromhex(Payload1A13)
        data = data.replace(OLD_OPEN_ID.encode(), NEW_OPEN_ID.encode())
        data = data.replace(OLD_ACCESS_TOKEN.encode(), NEW_ACCESS_TOKEN.encode())
        hex_data = data.hex()
        encrypted_data = encrypt_api(hex_data)
        Final_Payload = bytes.fromhex(encrypted_data)
        URL = MajorLoginRegionMena
        RESPONSE = requests.post(URL, headers=headers, data=Final_Payload, verify=False)
        combined_timestamp, key, iv, BASE64_TOKEN = self.parse_my_message(RESPONSE.content)
        if RESPONSE.status_code == 200:
            if len(RESPONSE.text) < 10:
                return False
            whisper_ip, whisper_port, online_ip, online_port = self.GET_PAYLOAD_BY_DATA(BASE64_TOKEN, NEW_ACCESS_TOKEN, 1)
            self.key = key
            self.iv = iv
            print(f"[{self.account_id}] Key: {key}, IV: {iv}")
            return (BASE64_TOKEN, key, iv, combined_timestamp, whisper_ip, whisper_port, online_ip, online_port)
        else:
            return False
    
    def get_tok(self):
        token_data = self.guest_token(self.account_id, self.password)
        if not token_data:
            print(f"[{self.account_id}] Failed to get token")
            self.restart()
            return
        
        token, key, iv, Timestamp, whisper_ip, whisper_port, online_ip, online_port = token_data
        print(f"[{self.account_id}] Whisper: {whisper_ip}:{whisper_port}")
        
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            account_id = decoded.get('account_id')
            encoded_acc = hex(account_id)[2:]
            hex_value = self.dec_to_hex(Timestamp)
            time_hex = hex_value
            BASE64_TOKEN_ = token.encode().hex()
            print(f"[{self.account_id}] Token decoded. Account ID: {account_id}")
        except Exception as e:
            print(f"[{self.account_id}] Error processing token: {e}")
            self.restart()
            return
        
        try:
            head = hex(len(encrypt_packet(BASE64_TOKEN_, key, iv)) // 2)[2:]
            length = len(encoded_acc)
            zeros = '00000000'
            if length == 9:
                zeros = '0000000'
            elif length == 8:
                zeros = '00000000'
            elif length == 10:
                zeros = '000000'
            elif length == 7:
                zeros = '000000000'
            else:
                print(f"[{self.account_id}] Unexpected length encountered")
            head = f'0115{zeros}{encoded_acc}{time_hex}00000{head}'
            final_token = head + encrypt_packet(BASE64_TOKEN_, key, iv)
        except Exception as e:
            print(f"[{self.account_id}] Error creating final token: {e}")
            self.restart()
            return
        
        self.connect(final_token, 'anything', key, iv, whisper_ip, whisper_port, online_ip, online_port)
        return final_token, key, iv
    
    def dec_to_hex(self, ask):
        ask_result = hex(ask)
        final_result = str(ask_result)[2:]
        if len(final_result) == 1:
            final_result = "0" + final_result
            return final_result
        else:
            return final_result
    
    def execute_command(self, command, *args):
        global shared_0500_info

        if '/bngx' in command[:5]:
                try:
                        if not self.socket_client or not self.is_socket_connected(self.socket_client):
                                return "Socket not connected, please wait for connection..."
                        
                        # args[0] = team code, args[1] = account name
                        team_code = args[0] if len(args) > 0 else None
                        account_name = args[1] if len(args) > 1 else "UnknownGhost"

                        if not team_code:
                                return "No team code provided for /bngx"

                        self.id = team_code
                        self.nm = account_name
                        print(f"[{self.account_id}] Executing /bngx for team code {self.id} with name {self.nm}")

                        # Master account logic
                        if self.account_id == MASTER_ACCOUNT_ID:
                                got_0500 = False
                                attempt_counter = 0

                                while not got_0500 and attempt_counter < 200:
                                        attempt_counter += 1
                                        print(f"[{self.account_id}] Attempt {attempt_counter} joining/exiting squad {self.id}...")

                                        self.socket_client.send(GenJoinSquadsPacket(self.id, self.key, self.iv))
                                        time.sleep(0.1)
                                        self.socket_client.send(ExiT('000000', self.key, self.iv))
                                        time.sleep(0.01)

                                        if self.DaTa2 and '0500' in self.DaTa2.hex()[0:4] and len(self.DaTa2.hex()) > 30:
                                                try:
                                                        self.dT = json.loads(DeCode_PackEt(self.DaTa2.hex()[10:]))
                                                        if "5" in self.dT and "data" in self.dT["5"] and "31" in self.dT["5"]["data"] and "1" in self.dT["5"]["data"]:
                                                                sq = self.dT["5"]["data"]["31"]["data"]
                                                                idT = self.dT["5"]["data"]["1"]["data"]
                                                                shared_0500_info['got'] = True
                                                                shared_0500_info['idT'] = idT
                                                                shared_0500_info['squad'] = sq
                                                                shared_0500_info['AutH'] = self.AutH

                                                                print(f"[{self.account_id}] Got 0500 with ID: {idT}")

                                                                # تأكد من الخروج قبل إرسال Ghost packet
                                                                self.socket_client.send(ExiT('000000', self.key, self.iv))
                                                                time.sleep(0.1)

                                                                # إرسال Ghost packet مرتين للتأكيد
                                                                for _ in range(1):
                                                                        self.socket_client.send(ghost_pakcet(idT, self.nm, sq, self.key, self.iv))
                                                                        time.sleep(0.1)
                                                                self.socket_client.send(ExiT('000000', self.key, self.iv))
                                                                time.sleep(0.2)
                                                                got_0500 = True
                                                        else:
                                                                print(f"[{self.account_id}] 0500 packet received but keys missing, skipping parse.")
                                                except Exception as parse_err:
                                                        print(f"[{self.account_id}] Error parsing 0500: {parse_err}")

                                if not got_0500:
                                        return f"Failed to get 0500 for team code {self.id} after {attempt_counter} attempts"
                                return f"/bngx master command executed successfully"

                        # Ghost account logic (uses master info)
                        else:
                                wait_attempts = 0
                                while not shared_0500_info['got'] and wait_attempts < 100:
                                        time.sleep(0.5)
                                        wait_attempts += 1

                                if not shared_0500_info['got']:
                                        return "Timeout waiting for master account to get 0500"

                                self.socket_client.send(GenJoinSquadsPacket(shared_0500_info['idT'], self.key, self.iv))
                                time.sleep(0.5)
                                self.socket_client.send(ExiT('000000', self.key, self.iv))
                                self.socket_client.send(ghost_pakcet(shared_0500_info['idT'], self.nm, shared_0500_info['squad'], self.key, self.iv))
                                
                                return f"/bngx ghost command executed using master data"

                except Exception as e:
                        print(f"[{self.account_id}] Error in execute_command: {e}")
                        return f"Error executing command: {e}"
        else:
                return f"Unknown command: {command}"
def load_accounts(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def cleanup():
    global shutting_down
    shutting_down = True
    print("Shutting down all clients...")
    for account_id, client in list(clients.items()):
        client.stop()
        del clients[account_id]
    print("Cleanup completed")

@app.route('/start_client', methods=['GET'])
def start_client():
    if shutting_down:
        return jsonify({'error': 'Server is shutting down'}), 503

    account_id = request.args.get('account_id')
    password = request.args.get('password')

    if not account_id or not password:
        return jsonify({'error': 'Account ID and password are required'}), 400

    if account_id in clients:
        return jsonify({'error': 'Client already running'}), 400

    client = TcpBotConnectMain(account_id, password)
    clients[account_id] = client

    client_thread = threading.Thread(target=client.run)
    client_thread.daemon = True
    client_thread.start()

    return jsonify({'message': f'Client {account_id} started successfully'}), 200

@app.route('/stop_client', methods=['GET'])
def stop_client():
    if shutting_down:
        return jsonify({'error': 'Server is shutting down'}), 503

    account_id = request.args.get('account_id')

    if not account_id:
        return jsonify({'error': 'Account ID is required'}), 400

    if account_id not in clients:
        return jsonify({'error': 'Client not found'}), 404

    client = clients[account_id]
    client.stop()
    del clients[account_id]

    return jsonify({'message': f'Client {account_id} stopped successfully'}), 200

@app.route('/execute_command', methods=['GET'])
def execute_command():
    if shutting_down:
        return jsonify({'error': 'Server is shutting down'}), 503

    account_id = request.args.get('account_id')
    command = request.args.get('command')
    client_id = request.args.get('client_id')

    if not account_id or not command:
        return jsonify({'error': 'Account ID and command are required'}), 400

    if account_id not in clients:
        return jsonify({'error': 'Client not found'}), 404

    client = clients[account_id]

    args = []
    if client_id:
        try:
            args.append(int(client_id))
        except ValueError:
            return jsonify({'error': 'Invalid client_id format'}), 400

    result = client.execute_command(command, *args)

    return jsonify({'result': result}), 200

@app.route('/list_clients', methods=['GET'])
def list_clients():
    return jsonify({'clients': list(clients.keys())}), 200

@app.route('/execute_command_all', methods=['GET'])
def execute_command_all():
    if shutting_down:
        return jsonify({'error': 'Server is shutting down'}), 503

    command = request.args.get('command')
    if not command:
        return jsonify({'error': 'Command parameter is required'}), 400

    # تقسيم الباراميتر على "=" أو المسافة
    if "=" in command:
        cmd, arg = command.split("=", 1)
    else:
        parts = command.split(" ", 1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else None

    # أسماء الحسابات لكل account_id
    ghost_names = {
    "3901729512": "insta: NR_CODEX",
    "3901723226": "NILAY IS THE BEST",
    "3901717899": "Telegram @buyfrom_nilay",
    "3901668081": "NILAY WILL BANNED YOU"
}


    results = {}
    for account_id, client in clients.items():
        account_name = ghost_names.get(str(account_id), str(account_id))
        if cmd == "/bngx" and arg:
            # تمرير الاسم مع team code
            result = client.execute_command(cmd, arg, account_name)
            results[account_id] = f"{result} | Name: {account_name}"
        else:
            results[account_id] = f"Unknown or invalid command: {command} | Name: {account_name}"

    return jsonify({'results': results})
    return jsonify({'results': results})
    return jsonify({'results': results})
@app.route('/shutdown', methods=['GET'])
def shutdown_server():
    global shutting_down
    shutting_down = True
    cleanup()
    return jsonify({'message': 'Server shutdown initiated'}), 200

def signal_handler(sig, frame):
    print('Received shutdown signal')
    cleanup()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(cleanup)

    try:
        accounts = load_accounts('accounts.json')
        for account_id, password in accounts.items():
            client = TcpBotConnectMain(account_id, password)
            clients[account_id] = client
            client_thread = threading.Thread(target=client.run)
            client_thread.daemon = True
            client_thread.start()
            time.sleep(3)
    except FileNotFoundError:
        print("No accounts file found. Starting without preloaded accounts.")

    try:
        app.run(host='0.0.0.0', port=15028, debug=False)
    except KeyboardInterrupt:
        print("Server stopped by user")
        cleanup()
