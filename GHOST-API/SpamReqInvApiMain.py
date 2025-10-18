import os
import sys
import re
import json
import time
import socket
import random
import logging
import binascii
import threading
from datetime import datetime
from time import sleep
import requests
import httpx
import urllib3
import jwt
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import google.protobuf
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.json_format import MessageToJson
from protobuf_decoder.protobuf_decoder import Parser
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
secertsq = None
from SpamReqInvApiSetting import *
def fix_num(num):
    fixed = ""
    count = 0
    num_str = str(num)
    for char in num_str:
        if char.isdigit():
            count += 1
        fixed += char
        if count == 3:
            fixed += "[c]"
            count = 0  
    return fixed
def encode_varint(num):
    if num < 0: raise ValueError("Number must be non-negative")
    out = []
    while True:
        b = num & 0x7F
        num >>= 7
        if num: b |= 0x80
        out.append(b)
        if not num: break
    return bytes(out)
def create_field(num, val):
    if isinstance(val, int): 
        return encode_varint((num<<3)|0) + encode_varint(val)
    if isinstance(val, (str,bytes)):
        v = val.encode() if isinstance(val,str) else val
        return encode_varint((num<<3)|2) + encode_varint(len(v)) + v
    if isinstance(val, dict):
        nested = create_packet(val)
        return encode_varint((num<<3)|2) + encode_varint(len(nested)) + nested
    return b""
def create_packet(fields):
    return b"".join(create_field(k,v) for k,v in fields.items())
def dec_to_hex(n): 
    return f"{n:02x}"
def encrypt_packet(plain_text, key, iv):
    plain_text = bytes.fromhex(plain_text)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    cipher_text = cipher.encrypt(pad(plain_text, AES.block_size))
    return cipher_text.hex()
def encrypt_api(plain_text):
    plain_text = bytes.fromhex(plain_text)
    key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    cipher_text = cipher.encrypt(pad(plain_text, AES.block_size))
    return cipher_text.hex()
def format_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
def aes_encrypt(data, key, iv):
    data = bytes.fromhex(data) if isinstance(data,str) else data
    return AES.new(key, AES.MODE_CBC, iv).encrypt(pad(data,16)).hex()
def parse_results(parsed_results):
    result_dict = {}
    for result in parsed_results:
        field_data = {}
        field_data["wire_type"] = result.wire_type
        if result.wire_type == "varint":
            field_data["data"] = result.data
        if result.wire_type == "string":
            field_data["data"] = result.data
        if result.wire_type == "bytes":
            field_data["data"] = result.data
        elif result.wire_type == "length_delimited":
            field_data["data"] = parse_results(result.data.results)
        result_dict[result.field] = field_data
    return result_dict
def get_available_room(input_text):
    try:
        parsed_results = Parser().parse(input_text)
        parsed_results_objects = parsed_results
        parsed_results_dict = parse_results(parsed_results_objects)
        json_data = json.dumps(parsed_results_dict)
        return json_data
    except Exception as e:
        print(f"error {e}")
        return None
def get_packet2(key,iv): 
    fields = {1:3, 2:{2:5,3:"en"}}
    packet = create_packet(fields).hex()+"7200"
    hlen = len(aes_encrypt(packet,key,iv))//2
    return bytes.fromhex("1215000000"+dec_to_hex(hlen)+aes_encrypt(packet,key,iv))
def OpenSquad(key, iv):
    fields = {1:1, 2:{2:"\u0001",3:1,4:1,5:"en",9:1,11:1,13:1,14:{2:5756,6:11,8:"1.109.5",9:3,10:2}}}
    packet = create_packet(fields).hex()
    encrypted_packet = aes_encrypt(packet, key, iv)
    hlen = len(encrypted_packet) // 2
    return bytes.fromhex("0515000000" + dec_to_hex(hlen) + encrypted_packet)
def ReqSquad(client_id, key, iv):
    fields = {1:2, 2:{1:int(client_id),2:"ME",4:1}}
    packet = create_packet(fields).hex()
    encrypted_packet = aes_encrypt(packet, key, iv)
    hlen = len(encrypted_packet) // 2
    return bytes.fromhex("0515000000" + dec_to_hex(hlen) + encrypted_packet)
def GeneratMsg(msg, cid, key, iv):
    fields = {1:1,2:{1:7141867918,2:int(cid),3:2,4:msg,5:int(datetime.now().timestamp()),7:2,9:{1:"TheIconicDevFOx",2:902000066,3:901037021,4:random.randint(301,330),5:901037021,8:"TheIconicDevFOx",10:2,11:2010,13:{1:2,2:1},14:{1:11017917409,2:8,3:"\u0010\u0015\b\n\u000b"}},10:"en",13:{1:"https://graph.facebook.com/v9.0/253082355523299/picture?width=160&height=160",2:1,3:1},14:{1:{1:random.choice([1,4]),2:1,3:random.randint(1,180),4:1,5:int(datetime.now().timestamp()),6:"en"}}}}
    packet = create_packet(fields).hex()
    encrypted_packet = aes_encrypt(packet, key, iv)
    hlen = len(encrypted_packet) // 2
    hlen_final = dec_to_hex(hlen)
    if len(hlen_final) == 2:
        final_packet = "1215000000" + hlen_final + encrypted_packet
    elif len(hlen_final) == 3:
        final_packet = "121500000" + hlen_final + encrypted_packet
    elif len(hlen_final) == 4:
        final_packet = "12150000" + hlen_final + encrypted_packet
    elif len(hlen_final) == 5:
        final_packet = "1215000" + hlen_final + encrypted_packet

    return bytes.fromhex(final_packet)
import requests , json , binascii , time , urllib3 , base64 , datetime , re ,socket , threading , random , os
from protobuf_decoder.protobuf_decoder import Parser
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad , unpad
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

Key , Iv = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56]) , bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

def EnC_AEs(HeX):
    cipher = AES.new(Key , AES.MODE_CBC , Iv)
    return cipher.encrypt(pad(bytes.fromhex(HeX), AES.block_size)).hex()
    
def DEc_AEs(HeX):
    cipher = AES.new(Key , AES.MODE_CBC , Iv)
    return unpad(cipher.decrypt(bytes.fromhex(HeX)), AES.block_size).hex()
    
def EnC_PacKeT(HeX , K , V): 
    return AES.new(K , AES.MODE_CBC , V).encrypt(pad(bytes.fromhex(HeX) ,16)).hex()
    
def DEc_PacKeT(HeX , K , V):
    return unpad(AES.new(K , AES.MODE_CBC , V).decrypt(bytes.fromhex(HeX)) , 16).hex()  

def EnC_Uid(H , Tp):
    e , H = [] , int(H)
    while H:
        e.append((H & 0x7F) | (0x80 if H > 0x7F else 0)) ; H >>= 7
    return bytes(e).hex() if Tp == 'Uid' else None

def EnC_Vr(N):
    if N < 0: ''
    H = []
    while True:
        BesTo = N & 0x7F ; N >>= 7
        if N: BesTo |= 0x80
        H.append(BesTo)
        if not N: break
    return bytes(H)
    
def DEc_Uid(H):
    n = s = 0
    for b in bytes.fromhex(H):
        n |= (b & 0x7F) << s
        if not b & 0x80: break
        s += 7
    return n
    
def CrEaTe_VarianT(field_number, value):
    field_header = (field_number << 3) | 0
    return EnC_Vr(field_header) + EnC_Vr(value)

def CrEaTe_LenGTh(field_number, value):
    field_header = (field_number << 3) | 2
    encoded_value = value.encode() if isinstance(value, str) else value
    return EnC_Vr(field_header) + EnC_Vr(len(encoded_value)) + encoded_value

def CrEaTe_ProTo(fields):
    packet = bytearray()    
    for field, value in fields.items():
        if isinstance(value, dict):
            nested_packet = CrEaTe_ProTo(value)
            packet.extend(CrEaTe_LenGTh(field, nested_packet))
        elif isinstance(value, int):
            packet.extend(CrEaTe_VarianT(field, value))           
        elif isinstance(value, str) or isinstance(value, bytes):
            packet.extend(CrEaTe_LenGTh(field, value))           
    return packet    
    
def DecodE_HeX(H):
    R = hex(H) 
    F = str(R)[2:]
    if len(F) == 1: F = "0" + F ; return F
    else: return F

def Fix_PackEt(parsed_results):
    result_dict = {}
    for result in parsed_results:
        field_data = {}
        field_data['wire_type'] = result.wire_type
        if result.wire_type == "varint":
            field_data['data'] = result.data
        if result.wire_type == "string":
            field_data['data'] = result.data
        if result.wire_type == "bytes":
            field_data['data'] = result.data
        elif result.wire_type == 'length_delimited':
            field_data["data"] = Fix_PackEt(result.data.results)
        result_dict[result.field] = field_data
    return result_dict

def DeCode_PackEt(input_text):
    try:
        parsed_results = Parser().parse(input_text)
        parsed_results_objects = parsed_results
        parsed_results_dict = Fix_PackEt(parsed_results_objects)
        json_data = json.dumps(parsed_results_dict)
        return json_data
    except Exception as e:
        print(f"error {e}")
        return None
                      
def xMsGFixinG(n):
    return '🗿'.join(str(n)[i:i + 3] for i in range(0 , len(str(n)) , 3))

def ArA_CoLor():
    Tp = ["32CD32" , "00BFFF" , "00FA9A" , "90EE90" , "FF4500" , "FF6347" , "FF69B4" , "FF8C00" , "FF6347" , "FFD700" , "FFDAB9" , "F0F0F0" , "F0E68C" , "D3D3D3" , "A9A9A9" , "D2691E" , "CD853F" , "BC8F8F" , "6A5ACD" , "483D8B" , "4682B4", "9370DB" , "C71585" , "FF8C00" , "FFA07A"]
    return random.choice(Tp)
    
def xBunnEr():
    bN = [902000306 , 902000305 , 902000003 , 902000016 , 902000017 , 902000019 , 902000020 , 902000021 , 902000023 , 902000070 , 902000087 , 902000108 , 902000011 , 902049020 , 902049018 , 902049017 , 902049016 , 902049015 , 902049003 , 902033016 , 902033017 , 902033018 , 902048018 , 902000306 , 902000305]
    return random.choice(bN)

def xSEndMsg(Msg , Tp , Tp2 , id , K , V):
    feilds = {1: id, 2: Tp2, 3: Tp, 4: Msg , 5: 1735129800, 7: 2, 9: {1: "xBesTo - C4­", 2: xBunnEr(), 3: 901048018, 4: 330, 5: 909034009, 8: "xBesTo - C4", 10: 1, 11: 1, 14: {1: 1158053040, 2: 8, 3: "\u0010\u0015\b\n\u000b\u0015\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005\u0006"}}, 10: "en", 13: {2: 1, 3: 1}, 14: {}}
    Pk = str(CrEaTe_ProTo(feilds).hex())
    Pk = "080112" + EnC_Uid(len(Pk) // 2 , Tp = 'Uid') + Pk
    return GeneRaTePk(str(Pk) , '1215' , K , V)

# By AbdeeLkarim BesTo

import requests , json , binascii , time , urllib3 , base64 , datetime , re ,socket , threading , random , os
from protobuf_decoder.protobuf_decoder import Parser
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad , unpad
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

Key , Iv = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56]) , bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

def EnC_AEs(HeX):
    cipher = AES.new(Key , AES.MODE_CBC , Iv)
    return cipher.encrypt(pad(bytes.fromhex(HeX), AES.block_size)).hex()
    
def DEc_AEs(HeX):
    cipher = AES.new(Key , AES.MODE_CBC , Iv)
    return unpad(cipher.decrypt(bytes.fromhex(HeX)), AES.block_size).hex()
    
def EnC_PacKeT(HeX , K , V): 
    return AES.new(K , AES.MODE_CBC , V).encrypt(pad(bytes.fromhex(HeX) ,16)).hex()
    
def DEc_PacKeT(HeX , K , V):
    return unpad(AES.new(K , AES.MODE_CBC , V).decrypt(bytes.fromhex(HeX)) , 16).hex()  

def EnC_Uid(H , Tp):
    e , H = [] , int(H)
    while H:
        e.append((H & 0x7F) | (0x80 if H > 0x7F else 0)) ; H >>= 7
    return bytes(e).hex() if Tp == 'Uid' else None

def EnC_Vr(N):
    if N < 0: ''
    H = []
    while True:
        BesTo = N & 0x7F ; N >>= 7
        if N: BesTo |= 0x80
        H.append(BesTo)
        if not N: break
    return bytes(H)
    
def DEc_Uid(H):
    n = s = 0
    for b in bytes.fromhex(H):
        n |= (b & 0x7F) << s
        if not b & 0x80: break
        s += 7
    return n
    
def CrEaTe_VarianT(field_number, value):
    field_header = (field_number << 3) | 0
    return EnC_Vr(field_header) + EnC_Vr(value)

def CrEaTe_LenGTh(field_number, value):
    field_header = (field_number << 3) | 2
    encoded_value = value.encode() if isinstance(value, str) else value
    return EnC_Vr(field_header) + EnC_Vr(len(encoded_value)) + encoded_value

def CrEaTe_ProTo(fields):
    packet = bytearray()    
    for field, value in fields.items():
        if isinstance(value, dict):
            nested_packet = CrEaTe_ProTo(value)
            packet.extend(CrEaTe_LenGTh(field, nested_packet))
        elif isinstance(value, int):
            packet.extend(CrEaTe_VarianT(field, value))           
        elif isinstance(value, str) or isinstance(value, bytes):
            packet.extend(CrEaTe_LenGTh(field, value))           
    return packet    
    
def DecodE_HeX(H):
    R = hex(H) 
    F = str(R)[2:]
    if len(F) == 1: F = "0" + F ; return F
    else: return F

def Fix_PackEt(parsed_results):
    result_dict = {}
    for result in parsed_results:
        field_data = {}
        field_data['wire_type'] = result.wire_type
        if result.wire_type == "varint":
            field_data['data'] = result.data
        if result.wire_type == "string":
            field_data['data'] = result.data
        if result.wire_type == "bytes":
            field_data['data'] = result.data
        elif result.wire_type == 'length_delimited':
            field_data["data"] = Fix_PackEt(result.data.results)
        result_dict[result.field] = field_data
    return result_dict

def DeCode_PackEt(input_text):
    try:
        parsed_results = Parser().parse(input_text)
        parsed_results_objects = parsed_results
        parsed_results_dict = Fix_PackEt(parsed_results_objects)
        json_data = json.dumps(parsed_results_dict)
        return json_data
    except Exception as e:
        print(f"error {e}")
        return None
                      
def xMsGFixinG(n):
    return '🗿'.join(str(n)[i:i + 3] for i in range(0 , len(str(n)) , 3))
def fix_num(num):
    fixed = ""
    count = 0
    num_str = str(num)
    for char in num_str:
        if char.isdigit():
            count += 1
        fixed += char
        if count == 3:
            fixed += "[c]"
            count = 0  
    return fixed
def SpamAddFriend(uid):
        try:
            url = f"https://spam-rose.vercel.app/send_friend?player_id={uid}"
            req = requests.get(url)
            data = req.json()
            for detail in data.get("details", []):
                status = detail.get("status")
                if status == "success":
                    return f"نجح ارسال سبام طلبات صداقة الى {fix_num(uid)}"
                else:
                    return "فشل ارسال سبام طلبات صداقة تحقق من الايدي او جرب في وقت لاحق"
        except Exception as e:
            return f"Error: {e}"   
def GetPlayerInfoRegionMena(uid):
    url = f"https://info-five-sooty.vercel.app/get?uid={uid}"
    req = requests.get(url)
    data = req.json()    
    account = data.get('AccountInfo', {})
    profile = data.get('AccountProfileInfo', {})
    guild = data.get('GuildInfo', {})
    pet = data.get('petInfo', {})
    credit = data.get('creditScoreInfo', {})
    social = data.get('socialinfo', {})
    def format_time(ts):
        try:
            return datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M:%S')
        except:
            return ts
    message1 = f"""
===== Account Info =====\nName: {account.get('AccountName')}\nLevel: {account.get('AccountLevel')}
Region: {account.get('AccountRegion')}
EXP: {fix_num(account.get('AccountEXP'))}
Likes: {fix_num(account.get('AccountLikes'))}
BR Rank: {fix_num(account.get('BrMaxRank'))} ({fix_num(account.get('BrRankPoint'))} points)
CS Rank: {fix_num(account.get('CsMaxRank'))} ({fix_num(account.get('CsRankPoint'))} points)
Equipped Weapon IDs: {fix_num(account.get('EquippedWeapon'))}
Account Type: {account.get('AccountType')}
Release Version: {account.get('ReleaseVersion')}
Created At: {fix_num(format_time(account.get('AccountCreateTime')))}
Last Login: {fix_num(format_time(account.get('AccountLastLogin')))}
"""
    message2 = f"""
===== Pet Info =====
Pet ID: {fix_num(pet.get('id'))}
Selected: {fix_num(pet.get('isSelected'))}
Level: {pet.get('level')}
Selected Skill ID: {fix_num(pet.get('selectedSkillId'))}
Skin ID: {fix_num(pet.get('skinId'))}
===== Credit Score Info =====
Credit Score: {fix_num(credit.get('creditScore'))}
Reward State: {fix_num(credit.get('rewardState'))}
===== Social Info =====
Account ID: {fix_num(social.get('accountId'))}
Language: {social.get('language')}
Rank Show: {fix_num(social.get('rankShow'))}
Signature: {social.get('signature')}
"""
    return [message1, message2]                      

def ArA_CoLor():
    Tp = [
        # 🔴 الأحمر
        "FF0000","DC143C","B22222","8B0000","A52A2A","CD5C5C","FA8072","E9967A","F08080","FF6347","FF4500","FF5F1F","FF2400","8B1A1A","FF6F61","FF7F50",
        
        # 🟠 البرتقالي
        "FFA500","FF8C00","FF7F00","FF7518","FF6700","E65100","FFB347","D2691E","CD853F","A0522D","8B4513","FFDEAD","FFE4B5","FFDAB9","FFE4C4","F4A460",
        
        # 🟡 الأصفر / الذهبي
        "FFFF00","FFD700","FFFACD","FAFAD2","EEE8AA","F0E68C","FFD700","EEDC82","DAA520","B8860B","CDAD00","FFC300","F1C40F","F39C12","FFEA00","FFF44F",
        
        # 🟢 الأخضر
        "00FF00","32CD32","7CFC00","7FFF00","ADFF2F","98FB98","90EE90","8FBC8F","66CDAA","20B2AA","3CB371","2E8B57","228B22","008000","006400","004225",
        
        # 🔵 الأزرق
        "0000FF","0000CD","00008B","191970","1E90FF","4169E1","4682B4","5F9EA0","6495ED","87CEEB","87CEFA","00BFFF","B0E0E6","ADD8E6","7B68EE","6A5ACD",
        
        # 🟣 البنفسجي / الوردي
        "800080","8A2BE2","9400D3","9932CC","BA55D3","DA70D6","DDA0DD","EE82EE","FF00FF","C71585","DB7093","FF1493","FF69B4","FFB6C1","FFC0CB","E75480",
        
        # ⚪ الرمادي / الأبيض / الأسود
        "FFFFFF","F8F8FF","F5F5F5","FFFAFA","F0F8FF","E6E6FA","DCDCDC","D3D3D3","C0C0C0","A9A9A9","808080","696969","2F4F4F","000000","778899","708090",
        
        # 🌈 ألوان زاهية إضافية
        "00FFFF","40E0D0","48D1CC","00CED1","1ABC9C","16A085","76EEC6","7FFFD4","AFEEEE","5F9EA0","48C9B0","45B39D","3498DB","2980B9","2471A3","154360",
        
        # 🎨 إضافات حديثة (درجات متنوعة)
        "E74C3C","C0392B","9B59B6","8E44AD","2874A6","1F618D","52BE80","27AE60","229954","1D8348","F39C12","D68910","CA6F1E","A04000","7E5109","6E2C00",
        
        # ✨ ألوان فاتحة/باستيل
        "FFDEAD","FFE4C4","FFEFD5","FFF5EE","FAEBD7","FFEBCD","FFF8DC","FDF5E6","F5DEB3","FFF0F5","E0FFFF","F0FFF0","F5FFFA","F0FFFF","F0F8FF","FFFACD"
    ]
    return random.choice(Tp)


    
def xBunnEr():
    bN = [902000306 , 902000305 , 902000003 , 902000016 , 902000017 , 902000019 , 902000020 , 902000021 , 902000023 , 902000070 , 902000087 , 902000108 , 902000011 , 902049020 , 902049018 , 902049017 , 902049016 , 902049015 , 902049003 , 902033016 , 902033017 , 902033018 , 902048018 , 902000306 , 902000305]
    return random.choice(bN)

def xSEndMsg(Msg , Tp , Tp2 , id , K , V):
    feilds = {1: id, 2: Tp2, 3: Tp, 4: Msg , 5: 1735129800, 7: 2, 9: {1: "xBesTo - C4­", 2: xBunnEr(), 3: 901048018, 4: 330, 5: 909034009, 8: "xBesTo - C4", 10: 1, 11: 1, 14: {1: 1158053040, 2: 8, 3: "\u0010\u0015\b\n\u000b\u0015\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005\u0006"}}, 10: "en", 13: {2: 1, 3: 1}, 14: {}}
    Pk = str(CrEaTe_ProTo(feilds).hex())
    Pk = "080112" + EnC_Uid(len(Pk) // 2 , Tp = 'Uid') + Pk
    return GeneRaTePk(str(Pk) , '1215' , K , V)

def Auth_Chat(idT, sq, K, V):
    fields = {
        1: 3,
        2: {
            1: idT,
            3: "fr",
            4: sq
        }
    }
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '1215' , K , V)
def xSendTeamMsg(msg, idT,  K, V):
    fields = {
    1: 1,
    2: {
        1: 12404281032,
        2: idT,
        4: msg,
        7: 2,
        10: "fr",
        9: {
            1: "C4 TEAM",
            2: xBunnEr(),
            4: 330,
            5: 827001005,
            8: "C4 TEAM",
            10: 1,
            11: 1,
            12: {
                1: 2
            },
            14: {
                1: 1158053040,
                2: 8,
                3: "\u0010\u0015\b\n\u000b\u0015\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005\u0006"
            }
        },
        13: {
            1: 2,
            2: 1
        },
        14:{}
    }
}
    
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '1215' , K , V)

def OpEnSq(K , V):
    fields = {1: 1, 2: {2: "\u0001", 3: 1, 4: 1, 5: "en", 9: 1, 11: 1, 13: 1, 14: {2: 5756, 6: 11, 8: "1.111.5", 9: 2, 10: 4}}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0515' , K , V)

def cHSq(Nu , Uid , K , V):
    fields = {1: 17, 2: {1: int(Uid), 2: 1, 3: int(Nu - 1), 4: 62, 5: "\u001a", 8: 5, 13: 329}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0515' , K , V)

def SEnd_InV(Nu , Uid , K , V):
    fields = {1: 2 , 2: {1: int(Uid) , 2: "ME" , 4: int(Nu)}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0515' , K , V)
    
def ExiT(id , K , V):
    fields = {
        1: 7,
        2: {
            1: int(11037044965)
        }
        }
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0515' , K , V)

def AuthClan(CLan_Uid , AuTh , K , V):
    fields = {1: 3, 2: {1: int(CLan_Uid) , 2: 1, 4: str(AuTh)}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '1201' , K , V) 
        
def GeT_Status(PLayer_Uid , K , V):
    PLayer_Uid = EnC_Uid(PLayer_Uid , Tp = 'Uid')
    if len(PLayer_Uid) == 8: Pk = f'080112080a04{PLayer_Uid}1005'
    elif len(PLayer_Uid) == 10: Pk = f"080112090a05{PLayer_Uid}1005"
    return GeneRaTePk(Pk , '0f15' , K , V)
           
def SPam_Room(Uid , Rm , Nm , K , V):
    fields = {1: 78, 2: {1: int(Rm), 2: f"[{ArA_CoLor()}]{Nm}", 3: {2: 1, 3: 1}, 4: 330, 5: 1, 6: 201, 10: xBunnEr(), 11: int(Uid), 12: 1}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0e15' , K , V)

def Join_Room(room_id , K , V):
    fields = {1: 3, 2: {1: int(room_id), 8: {1: "IDC1", 2: 3000, 3: "ME"}, 9: "\x01\t\n\x12\x19 ", 10: 1, 12: b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01", 13: 3, 14: 3, 16: "ME"}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0e10' , K , V)

def SPamSq(Uid , K , V): 
    fields = {1: 33, 2: {1: int(Uid) , 2: 'ME', 3: 1, 4: 1, 7: 330, 8: 19459, 9: 100, 12: 1, 16: 1, 17: {2: 94, 6: 11, 8: '1.111.5', 9: 3, 10: 2}, 18: 201, 23: {2: 1, 3: 1}, 24: xBunnEr() , 26: {}, 28: {}}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0515' , K , V)

def AccEpT(PLayer_Uid , AuTh_CodE_Sq , K , V): 
    fields = {1: 4, 2: {1: int(PLayer_Uid), 3: int(PLayer_Uid), 4: "\u0001\u0007\t\n\u0012\u0019\u001a ", 8: 1, 9: {2: 1393, 4: "wW_T", 6: 11, 8: "1.111.5", 9: 3, 10: 2}, 10: AuTh_CodE_Sq, 12: 1, 13: "en", 16: "OR"}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0515' , K , V)

def GenJoinSquadsPacket(code, key, iv):
    fields = {}
    fields[1] = 4
    fields[2] = {}
    fields[2][4] = bytes.fromhex("01090a0b121920")
    fields[2][5] = str(code)
    fields[2][6] = 6
    fields[2][8] = 1
    fields[2][9] = {}
    fields[2][9][2] = 800
    fields[2][9][6] = 11
    fields[2][9][8] = "1.111.1"
    fields[2][9][9] = 5
    fields[2][9][10] = 1
    print(fields)
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), '0515', key, iv)
     #1750287629500765351_vfhkisb7hv 8679231987
def ghost_pakcet(player_id , nm , secret_code , key ,iv):
    fields = {
        1: 61,
        2: {
            1: int(player_id),  
            2: {
                1: int(player_id),  
                2: 1159,  
                3: f"[b][c][{ArA_CoLor()}]{nm}",  
                5: 12,  
                6: 15,
                7: 1,
                8: {
                    2: 1,
                    3: 1,
                },
                9: 3,
            },
            3: secret_code,},}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), '0515', key, iv)
                                   
def _V(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1
        r |= (c & 0x7F) << s
        if c < 0x80: break
        s += 7
    return r, i

def PrOtO(hx):
    b, i, R = bytes.fromhex(hx), 0, {}
    while i < len(b):
        H, i = _V(b, i)
        F, T = H >> 3, H & 7
        if T == 0:
            R[F], i = _V(b, i)
        elif T == 2:
            L, i = _V(b, i)
            S = b[i:i+L]; i += L
            try: R[F] = S.decode()
            except:
                try: R[F] = PrOtO(S.hex())
                except: R[F] = S
        elif T == 5:
            R[F] = int.from_bytes(b[i:i+4], 'little'); i += 4
        else:
            raise ValueError(f'Unknown wire type: {T}')
    return R
    
def GeT_KEy(obj , target):
    values = []
    def collect(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == target:
                    values.append(v)
                collect(v)
        elif isinstance(o, list):
            for v in o:
                collect(v)
    collect(obj)
    return values[-1] if values else None
 
 
def GeneRaTePk(Pk , N , K , V):
    PkEnc = EnC_PacKeT(Pk , K , V)
    _ = DecodE_HeX(int(len(PkEnc) // 2))
    if len(_) == 2: HeadEr = N + "000000"
    elif len(_) == 3: HeadEr = N + "00000"
    elif len(_) == 4: HeadEr = N + "0000"
    elif len(_) == 5: HeadEr = N + "000"
    return bytes.fromhex(HeadEr + _ + PkEnc)
    
def GuiLd_AccEss(Tg , Nm , Uid , BLk , OwN , AprV):
    return Tg in Nm and Uid not in BLk and Uid in (OwN | AprV)
            
def ChEck_Commande(id):
    return "<" not in id and ">" not in id and "[" not in id and "]" not in id
        
def L_DaTa():
    load = lambda f: json.load(open(f)) if os.path.exists(f) else {}
    return map(load, ["BesTo_CLan_LiKes.json" , "BesTo_RemaininG_LiKes.json" , "BesTo_RemaininG_Room.json"])
       
def ChEck_Limit_CLan(Uid , STaTus):
    data , max_use , file = (like_data_clan, 10, "BesTo_CLan_LiKes.json") if STaTus == "like" else ''
    t , limit = time.time(), 86400
    u = data.get(str(Uid), {"count": 0, "start_time": t})    
    if t - u["start_time"] >= limit:
        u = {"count": 0, "start_time": t}
    if u["count"] < max_use:
        u["count"] += 1
        data[str(Uid)] = u
        json.dump(data , open(file, "w"))
        return f"{max_use - u['count']}" , datetime.fromtimestamp(u["start_time"] + limit).strftime("%I:%M %p - %d/%m/%y")
    return False , datetime.fromtimestamp(u["start_time"] + limit).strftime("%I:%M %p - %d/%m/%y")

def ChEck_Limit(Uid , STaTus):
    data , max_use , file = (like_data, 10, "BesTo_RemaininG_LiKes.json") if STaTus == "like" else (room_data, 10, "BesTo_RemaininG_Room.json")
    t , limit = time.time(), 86400
    u = data.get(str(Uid), {"count": 0, "start_time": t})    
    if t - u["start_time"] >= limit:
        u = {"count": 0, "start_time": t}
    if u["count"] < max_use:
        u["count"] += 1
        data[str(Uid)] = u
        json.dump(data , open(file, "w"))
        return f"{max_use - u['count']}" , datetime.fromtimestamp(u["start_time"] + limit).strftime("%I:%M %p - %d/%m/%y")
    return False , datetime.fromtimestamp(u["start_time"] + limit).strftime("%I:%M %p - %d/%m/%y")
    
f = 'blacklist.txt'
approvee = 'approved.txt'
black , approve = [] , []

def load_blacklist():
    global black
    try: 
        with open(f, 'r') as file: 
            black = [line.strip() for line in file if line.strip()]
    except: black = []

def encrypt_uids():
    global black
    try: 
        if black: black = [EnC_Uid(uid , Tp = 'Uid') for uid in black]
    except: 
        try: open(f, 'w').close()
        except: pass
        load_blacklist()

if not black: open(f, 'w').close()

def load_approve():
    global approve
    try: 
        with open(approvee, 'r') as file: approve = [line.strip() for line in file if line.strip()]
    except: approve = []

def encrypt_uids2():
    global approve
    try: 
        if approve: approve = [EnC_Uid(uid , Tp = 'Uid') for uid in approve]
    except: 
        try: open(approvee, 'w').close()
        except: pass
        load_approve()

if not approve: open(approvee, 'w').close()
               
def Add_Uid(user_id):
    with open(f, 'r') as file: lines = file.read().splitlines()
    if str(user_id) not in lines:
        with open(f, 'a') as file: file.write(f"{user_id}\n")

def Remove_Uid(f, player_uid):
    try:
        with open(f, 'r+') as file: lines = file.readlines() ; file.seek(0), file.truncate(), file.writelines(l for l in lines if l.strip() != player_uid) ; return True
    except FileNotFoundError: return False
        
def A(user_id):
    with open(approvee, 'r') as file: lines = file.read().splitlines()
    if str(user_id) not in lines:
        with open(approvee, 'a') as file: file.write(f"{user_id}\n")

def D(approvee, player_uid):
    try:
        with open(approvee, 'r+') as file: lines = file.readlines() ; file.seek(0), file.truncate(), file.writelines(l for l in lines if l.strip() != player_uid) ; return True
    except FileNotFoundError: return False        

def Clear():
    try:
        open(f, 'w').close() ; black.clear() ; return True
    except: return False
                   
def Add_Black(user_id):
    Add_Uid(user_id)
    if EnC_Uid(user_id , Tp = 'Uid') not in black: black.append(EnC_Uid(user_id , Tp = 'Uid')) ; return True
    else: return False 
    
def Rem_Black(user_id):
    user_id_encrypted = EnC_Uid(user_id , Tp = 'Uid')
    if user_id_encrypted in black: black.remove(user_id_encrypted) ; Remove_Uid(f , user_id) ; return True
    else: return False       

def Show_Uids():
    try:
        with open(f) as file: return "\n".join(sorted(file.read().splitlines(), key=int)) or False
    except (FileNotFoundError, ValueError): return False 

def Approved(user_id):
    A(user_id)
    if EnC_Uid(user_id , Tp = 'Uid') not in approve: approve.append(EnC_Uid(user_id , Tp = 'Uid')) ; return True
    else: return False 
    
def DeApproved(user_id):
    user_id_encrypted = EnC_Uid(user_id , Tp = 'Uid')
    if user_id_encrypted in approve: approve.remove(user_id_encrypted) ; D(approvee , user_id) ; return True
    else: return False        
        
def Show_Approvs():
    try: 
        with open(approvee) as file: return "\n".join(sorted(file.read().splitlines(), key=int)) or False
    except (FileNotFoundError, ValueError): return False 
        
def Clear_Approvs():
    try: 
        open(approvee, 'w').close() ; approve.clear() ; return True
    except: return False
    
load_blacklist() ; encrypt_uids()    
load_approve() ; encrypt_uids2()   
like_data_clan , like_data , room_data = L_DaTa()
            

def Auth_Chat(idT, sq, K, V):
    fields = {
        1: 3,
        2: {
            1: idT,
            3: "fr",
            4: sq
        }
    }
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '1215' , K , V)
def xSendTeamMsg(msg, idT,  K, V):
    fields = {
    1: 1,
    2: {
        1: 12404281032,
        2: idT,
        4: msg,
        7: 2,
        10: "fr",
        9: {
            1: "C4 TEAM",
            2: xBunnEr(),
            4: 330,
            5: 827001005,
            8: "C4 TEAM",
            10: 1,
            11: 1,
            12: {
                1: 2
            },
            14: {
                1: 1158053040,
                2: 8,
                3: "\u0010\u0015\b\n\u000b\u0015\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005\u0006"
            }
        },
        13: {
            1: 2,
            2: 1
        },
        14:{}
    }
}
    
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '1215' , K , V)

def OpEnSq(K , V):
    fields = {1: 1, 2: {2: "\u0001", 3: 1, 4: 1, 5: "en", 9: 1, 11: 1, 13: 1, 14: {2: 5756, 6: 11, 8: "1.111.5", 9: 2, 10: 4}}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0515' , K , V)

def cHSq(Nu , Uid , K , V):
    fields = {1: 17, 2: {1: int(Uid), 2: 1, 3: int(Nu - 1), 4: 62, 5: "\u001a", 8: 5, 13: 329}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0515' , K , V)

def SEnd_InV(Nu , Uid , K , V):
    fields = {1: 2 , 2: {1: int(Uid) , 2: "ME" , 4: int(Nu)}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0515' , K , V)
    
def ExiT(id , K , V):
    fields = {
        1: 7,
        2: {
            1: int(11037044965)
        }
        }
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0515' , K , V)

def AuthClan(CLan_Uid , AuTh , K , V):
    fields = {1: 3, 2: {1: int(CLan_Uid) , 2: 1, 4: str(AuTh)}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '1201' , K , V) 
        
def GeT_Status(PLayer_Uid , K , V):
    PLayer_Uid = EnC_Uid(PLayer_Uid , Tp = 'Uid')
    if len(PLayer_Uid) == 8: Pk = f'080112080a04{PLayer_Uid}1005'
    elif len(PLayer_Uid) == 10: Pk = f"080112090a05{PLayer_Uid}1005"
    return GeneRaTePk(Pk , '0f15' , K , V)
           
def SPam_Room(Uid , Rm , Nm , K , V):
    fields = {1: 78, 2: {1: int(Rm), 2: f"[{ArA_CoLor()}]{Nm}", 3: {2: 1, 3: 1}, 4: 330, 5: 1, 6: 201, 10: xBunnEr(), 11: int(Uid), 12: 1}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0e15' , K , V)

def Join_Room(room_id , K , V):
    fields = {1: 3, 2: {1: int(room_id), 8: {1: "IDC1", 2: 3000, 3: "ME"}, 9: "\x01\t\n\x12\x19 ", 10: 1, 12: b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01", 13: 3, 14: 3, 16: "ME"}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0e10' , K , V)

def SPamSq(Uid , K , V): 
    fields = {1: 33, 2: {1: int(Uid) , 2: 'ME', 3: 1, 4: 1, 7: 330, 8: 19459, 9: 100, 12: 1, 16: 1, 17: {2: 94, 6: 11, 8: '1.111.5', 9: 3, 10: 2}, 18: 201, 23: {2: 1, 3: 1}, 24: xBunnEr() , 26: {}, 28: {}}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0515' , K , V)

def AccEpT(PLayer_Uid , AuTh_CodE_Sq , K , V): 
    fields = {1: 4, 2: {1: int(PLayer_Uid), 3: int(PLayer_Uid), 4: "\u0001\u0007\t\n\u0012\u0019\u001a ", 8: 1, 9: {2: 1393, 4: "wW_T", 6: 11, 8: "1.111.5", 9: 3, 10: 2}, 10: AuTh_CodE_Sq, 12: 1, 13: "en", 16: "OR"}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0515' , K , V)

def GenJoinSquadsPacket(code, key, iv):
    fields = {}
    fields[1] = 4
    fields[2] = {}
    fields[2][4] = bytes.fromhex("01090a0b121920")
    fields[2][5] = str(code)
    fields[2][6] = 6
    fields[2][8] = 1
    fields[2][9] = {}
    fields[2][9][2] = 800
    fields[2][9][6] = 11
    fields[2][9][8] = "1.111.1"
    fields[2][9][9] = 5
    fields[2][9][10] = 1
    print(fields)
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), '0515', key, iv)
     #1750287629500765351_vfhkisb7hv 8679231987
def ghost_pakcet(player_id , nm , secret_code , key ,iv):
    fields = {
        1: 61,
        2: {
            1: int(player_id),  
            2: {
                1: int(player_id),  
                2: 1159,  
                3: f"[b][c][{ArA_CoLor()}]{nm}",  
                5: 12,  
                6: 15,
                7: 1,
                8: {
                    2: 1,
                    3: 1,
                },
                9: 3,
            },
            3: secret_code,},}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), '0515', key, iv)
                                   
def _V(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1
        r |= (c & 0x7F) << s
        if c < 0x80: break
        s += 7
    return r, i

def PrOtO(hx):
    b, i, R = bytes.fromhex(hx), 0, {}
    while i < len(b):
        H, i = _V(b, i)
        F, T = H >> 3, H & 7
        if T == 0:
            R[F], i = _V(b, i)
        elif T == 2:
            L, i = _V(b, i)
            S = b[i:i+L]; i += L
            try: R[F] = S.decode()
            except:
                try: R[F] = PrOtO(S.hex())
                except: R[F] = S
        elif T == 5:
            R[F] = int.from_bytes(b[i:i+4], 'little'); i += 4
        else:
            raise ValueError(f'Unknown wire type: {T}')
    return R
    
def GeT_KEy(obj , target):
    values = []
    def collect(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == target:
                    values.append(v)
                collect(v)
        elif isinstance(o, list):
            for v in o:
                collect(v)
    collect(obj)
    return values[-1] if values else None
 
 
def GeneRaTePk(Pk , N , K , V):
    PkEnc = EnC_PacKeT(Pk , K , V)
    _ = DecodE_HeX(int(len(PkEnc) // 2))
    if len(_) == 2: HeadEr = N + "000000"
    elif len(_) == 3: HeadEr = N + "00000"
    elif len(_) == 4: HeadEr = N + "0000"
    elif len(_) == 5: HeadEr = N + "000"
    return bytes.fromhex(HeadEr + _ + PkEnc)
    
def GuiLd_AccEss(Tg , Nm , Uid , BLk , OwN , AprV):
    return Tg in Nm and Uid not in BLk and Uid in (OwN | AprV)
            
def ChEck_Commande(id):
    return "<" not in id and ">" not in id and "[" not in id and "]" not in id
        
def L_DaTa():
    load = lambda f: json.load(open(f)) if os.path.exists(f) else {}
    return map(load, ["BesTo_CLan_LiKes.json" , "BesTo_RemaininG_LiKes.json" , "BesTo_RemaininG_Room.json"])
       
def ChEck_Limit_CLan(Uid , STaTus):
    data , max_use , file = (like_data_clan, 10, "BesTo_CLan_LiKes.json") if STaTus == "like" else ''
    t , limit = time.time(), 86400
    u = data.get(str(Uid), {"count": 0, "start_time": t})    
    if t - u["start_time"] >= limit:
        u = {"count": 0, "start_time": t}
    if u["count"] < max_use:
        u["count"] += 1
        data[str(Uid)] = u
        json.dump(data , open(file, "w"))
        return f"{max_use - u['count']}" , datetime.fromtimestamp(u["start_time"] + limit).strftime("%I:%M %p - %d/%m/%y")
    return False , datetime.fromtimestamp(u["start_time"] + limit).strftime("%I:%M %p - %d/%m/%y")

def ChEck_Limit(Uid , STaTus):
    data , max_use , file = (like_data, 10, "BesTo_RemaininG_LiKes.json") if STaTus == "like" else (room_data, 10, "BesTo_RemaininG_Room.json")
    t , limit = time.time(), 86400
    u = data.get(str(Uid), {"count": 0, "start_time": t})    
    if t - u["start_time"] >= limit:
        u = {"count": 0, "start_time": t}
    if u["count"] < max_use:
        u["count"] += 1
        data[str(Uid)] = u
        json.dump(data , open(file, "w"))
        return f"{max_use - u['count']}" , datetime.fromtimestamp(u["start_time"] + limit).strftime("%I:%M %p - %d/%m/%y")
    return False , datetime.fromtimestamp(u["start_time"] + limit).strftime("%I:%M %p - %d/%m/%y")
    
f = 'blacklist.txt'
approvee = 'approved.txt'
black , approve = [] , []

def load_blacklist():
    global black
    try: 
        with open(f, 'r') as file: 
            black = [line.strip() for line in file if line.strip()]
    except: black = []

def encrypt_uids():
    global black
    try: 
        if black: black = [EnC_Uid(uid , Tp = 'Uid') for uid in black]
    except: 
        try: open(f, 'w').close()
        except: pass
        load_blacklist()

if not black: open(f, 'w').close()

def load_approve():
    global approve
    try: 
        with open(approvee, 'r') as file: approve = [line.strip() for line in file if line.strip()]
    except: approve = []

def encrypt_uids2():
    global approve
    try: 
        if approve: approve = [EnC_Uid(uid , Tp = 'Uid') for uid in approve]
    except: 
        try: open(approvee, 'w').close()
        except: pass
        load_approve()

if not approve: open(approvee, 'w').close()
               
def Add_Uid(user_id):
    with open(f, 'r') as file: lines = file.read().splitlines()
    if str(user_id) not in lines:
        with open(f, 'a') as file: file.write(f"{user_id}\n")

def Remove_Uid(f, player_uid):
    try:
        with open(f, 'r+') as file: lines = file.readlines() ; file.seek(0), file.truncate(), file.writelines(l for l in lines if l.strip() != player_uid) ; return True
    except FileNotFoundError: return False
        
def A(user_id):
    with open(approvee, 'r') as file: lines = file.read().splitlines()
    if str(user_id) not in lines:
        with open(approvee, 'a') as file: file.write(f"{user_id}\n")

def D(approvee, player_uid):
    try:
        with open(approvee, 'r+') as file: lines = file.readlines() ; file.seek(0), file.truncate(), file.writelines(l for l in lines if l.strip() != player_uid) ; return True
    except FileNotFoundError: return False        

def Clear():
    try:
        open(f, 'w').close() ; black.clear() ; return True
    except: return False
                   
def Add_Black(user_id):
    Add_Uid(user_id)
    if EnC_Uid(user_id , Tp = 'Uid') not in black: black.append(EnC_Uid(user_id , Tp = 'Uid')) ; return True
    else: return False 
    
def Rem_Black(user_id):
    user_id_encrypted = EnC_Uid(user_id , Tp = 'Uid')
    if user_id_encrypted in black: black.remove(user_id_encrypted) ; Remove_Uid(f , user_id) ; return True
    else: return False       

def Show_Uids():
    try:
        with open(f) as file: return "\n".join(sorted(file.read().splitlines(), key=int)) or False
    except (FileNotFoundError, ValueError): return False 

def Approved(user_id):
    A(user_id)
    if EnC_Uid(user_id , Tp = 'Uid') not in approve: approve.append(EnC_Uid(user_id , Tp = 'Uid')) ; return True
    else: return False 
    
def DeApproved(user_id):
    user_id_encrypted = EnC_Uid(user_id , Tp = 'Uid')
    if user_id_encrypted in approve: approve.remove(user_id_encrypted) ; D(approvee , user_id) ; return True
    else: return False        
        
def Show_Approvs():
    try: 
        with open(approvee) as file: return "\n".join(sorted(file.read().splitlines(), key=int)) or False
    except (FileNotFoundError, ValueError): return False 
        
def Clear_Approvs():
    try: 
        open(approvee, 'w').close() ; approve.clear() ; return True
    except: return False
    
load_blacklist() ; encrypt_uids()    
load_approve() ; encrypt_uids2()   
like_data_clan , like_data , room_data = L_DaTa()
