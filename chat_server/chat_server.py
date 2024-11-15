import socket
import json
import message_pb2 as pb
import select
from models import (Client, Room)
import argparse
import queue
import threading
import sys

clients = []
client_queue=queue.Queue()
lock = threading.Lock()  
condition = threading.Condition(lock)  
rooms = []
quit_flag = False
BUFFER_SIZE = 65536
type=None

def send_json_message(client, message):
    '''
    시스템 메세지를 JSON 형식으로 Serialize하고 클라이언트에게 보낸다.

    :param client: Client 객체
    :param message: 보낼 메세지
    '''
    serialized = json.dumps(message).encode('utf-8') 
    length_prefix = len(serialized).to_bytes(2, byteorder='big')  
    client.sock.sendall(length_prefix + serialized) 

def send_proto_message(client, message):
    '''
    시스템 메세지를 Protobuf 형식으로 Serialize하고 클라이언트에게 보낸다.

    :param client: Client 객체
    :param message: 보낼 메세지
    '''
    system_message = pb.SCSystemMessage()
    system_message.text = message

    serialized_system_message = system_message.SerializeToString()

    type_message = pb.Type()
    type_message.type = pb.Type.MessageType.SC_SYSTEM_MESSAGE

    serialized_type_message = type_message.SerializeToString()

    length_prefix_type = len(serialized_type_message).to_bytes(2, byteorder='big')
    length_prefix_system = len(serialized_system_message).to_bytes(2, byteorder='big')

    client.sock.sendall(length_prefix_type + serialized_type_message + length_prefix_system + serialized_system_message)

def notify_room_members(room_id, message, exclude_sock=None):
    '''
    클라이언트가 속한 방의 모든 클라이언트에게 JSON 형식으로 시스템 메세지를 보낸다.

    :param room_id: Client의 room_id
    :param message: 보낼 시스템 메세지
    :param exclude_sock: Client의 sock
    '''   
    for room in rooms:
        if room.id == room_id:
            for member in room.members:
                if member.sock != exclude_sock:
                    system_message = {
                    'type': 'SCSystemMessage',
                    'text': message
                    }
                    send_json_message(member, system_message)

def notify_room_pmembers(room_id, message, exclude_sock=None):
    '''
    클라이언트가 속한 방의 모든 클라이언트에게 Protobuf 형식으로 시스템 메세지를 보낸다.

    :param room_id: Client의 room_id
    :param message: 보낼 시스템 메세지
    :param exclude_sock: Client의 sock
    '''
    for room in rooms:
        if room.id == room_id:
            for member in room.members:
                if member.sock != exclude_sock:
                    send_proto_message(member,message)

def handle_name(client, command_json):
    new_nickname = command_json['name']
    client.nickname = new_nickname
    system_message = {
        'type': 'SCSystemMessage',
        'text': f"이름이 {new_nickname}으로 변경되었습니다.\n"
    }
    send_json_message(client, system_message)

    if client.room_id != -1:
        notify_room_members(client.room_id, f"이름이 {new_nickname}으로 변경되었습니다.", client.sock)
    
    return
    
def handle_rooms(client,command_json):
    rooms_message = {
        'type': 'SCRoomsResult',
        'rooms': []
    }
    if not rooms:
        rooms_message['rooms'] = [] 

    else:
        for room in rooms:
            room_info = {
                'roomId': room.id,
                'title': room.title,
                'members': [member.nickname for member in room.members]
            }
            rooms_message['rooms'].append(room_info)

    send_json_message(client, rooms_message)   

def handle_create_room(client, command_json):
    if client.room_id != -1:
        error_message = {
        'type': 'SCSystemMessage',
        'text': f"대화 방에 있을 때는 방을 개설할 수 없습니다.\n"
    }
        send_json_message(client, error_message)

    else:        
        room_title = command_json['title']
        new_room = Room(len(rooms) + 1, room_title)
        new_room.members.append(client)
        rooms.append(new_room)
        client.room_id = new_room.id
        success_message = f"방제 [{room_title}] 방에 입장했습니다.\n"
        system_message = {
            'type': 'SCSystemMessage',
            'text': success_message
                        }
        send_json_message(client, system_message)

def handle_join_room(client, command_json):
    room_id = command_json['roomId']

    if client.room_id != -1:
        error_message = {
            'type': 'SCSystemMessage',
            'text': "대화 방에 있을 때는 다른 방에 들어갈 수 없습니다.\n"
        }
        send_json_message(client, error_message)
        
    else:
        room = next((r for r in rooms if r.id == room_id), None)
        
        if room is None:  
            error_message = {
                'type': 'SCSystemMessage',
                'text': "대화방이 존재하지 않습니다.\n"
            }
            send_json_message(client, error_message)
            
        else:
            room.members.append(client)
            client.room_id = room_id

            success_message = {
                'type': 'SCSystemMessage',
                'text': f"방제[{room.title}] 방에 입장했습니다.\n"
            }
            send_json_message(client, success_message)

            notify_room_members(client.room_id, f"[{client.nickname}]님이 입장했습니다.\n",client.sock)


def handle_leave_room(client,command_json):
    if client.room_id == -1:
        error_message = {
        'type': 'SCSystemMessage',
        'text': f"현재 대화방에 들어가 있지 않습니다.\n"
    }
        send_json_message(client, error_message)

    else:
        room_id = client.room_id
        notify_room_members(room_id, f"[{client.nickname}]님이 퇴장했습니다.\n", client.sock)
        
        room = next((r for r in rooms if r.id == room_id), None)
        if room:
            room.members = [member for member in room.members if member.nickname != client.nickname]
        
        leave_message = f"방제[{rooms[room_id - 1].title}] 대화 방에서 퇴장했습니다.\n"
        system_message = {
            'type': 'SCSystemMessage',
            'text': leave_message
                        }
        send_json_message(client, system_message)
        client.room_id = -1

def handle_chat(client, command_json):
    print('handle_chat')
    if client.room_id == -1:
        error_message = {
        'type': 'SCSystemMessage',
        'text': f"현재 대화방에 들어가 있지 않습니다.\n"
    }
        send_json_message(client, error_message)

    else:
            for c in clients:
                print('c',c)
                if c.sock != client.sock and c.room_id == client.room_id:
                    message_text = command_json['text']
                    chat_message = {
                    'type': 'SCChat',
                    'text': message_text,
                    "member":client.nickname
                                    }
                    send_json_message(c, chat_message)

def handle_shutdown(client,command_json):
    global quit_flag
    quit_flag=True

message_handlers = {
    'CSName': handle_name,
    'CSRooms': handle_rooms,
    'CSCreateRoom': handle_create_room,
    'CSJoinRoom': handle_join_room,
    'CSLeaveRoom': handle_leave_room,
    'CSShutdown': handle_shutdown,
    'CSChat':handle_chat
    
}

def handle_protobuf_name(client, cs_name):
    print('handle_proto_name',cs_name.name)
    new_nickname = cs_name.name

    if cs_name.name:
        client.nickname = new_nickname
        system_message = f"이름이 {new_nickname}으로 변경되었습니다.\n"
        send_proto_message(client,system_message)

        if client.room_id != -1:
            notify_room_pmembers(client.room_id, f"이름이 {new_nickname}으로 변경되었습니다.\n",client.sock)

def handle_protobuf_rooms(client):
    rooms_message = pb.SCRoomsResult()

    for room in rooms:  
        room_info = rooms_message.rooms.add() 
        room_info.roomId = room.id
        room_info.title = room.title
        room_info.members.extend([member.nickname for member in room.members])  

    serialized_rooms_message = rooms_message.SerializeToString()

    type_message = pb.Type()
    type_message.type = pb.Type.MessageType.SC_ROOMS_RESULT

    serialized_type_message = type_message.SerializeToString()

    length_prefix_type = len(serialized_type_message).to_bytes(2, byteorder='big')
    length_prefix_rooms = len(serialized_rooms_message).to_bytes(2, byteorder='big')

    client.sock.sendall(length_prefix_type + serialized_type_message + length_prefix_rooms + serialized_rooms_message)

def handle_protobuf_create_room(client, cs_create_room):
    if client.room_id != -1:
        error_message = "대화 방에 있을 때는 방을 개설할 수 없습니다.\n"
        send_proto_message(client,error_message)
        return
    
    if cs_create_room.title:
        room_title = cs_create_room.title
        new_room = Room(len(rooms) + 1, room_title)
        new_room.members.append(client)
        rooms.append(new_room)
        client.room_id = new_room.id
        system_message = f"방제[{room_title}] 방에 입장했습니다.\n"
        send_proto_message(client,system_message)

def handle_protobuf_join_room(client, cs_join_room):   
    room_id = cs_join_room.roomId

    if client.room_id!=-1:
        error_message = "대화 방에 있을 때는 다른 방에 들어갈 수 없습니다.\n"
        send_proto_message(client,error_message)
        return
    
    room = next((r for r in rooms if r.id == room_id), None)
    
    if room is None:  
        error_message = "대화방이 존재하지 않습니다.\n"
        send_proto_message(client,error_message)
        
    else:    
        room.members.append(client)
        client.room_id = room_id

        success_message = f"방제[{room.title}] 방에 입장했습니다.\n"
        send_proto_message(client,success_message)
    
        notify_room_pmembers(client.room_id, f"[{client.nickname}]님이 입장했습니다.\n",client.sock)        

def handle_protobuf_leave_room(client):
    if client.room_id == -1:
        error_message = "현재 대화방에 들어가 있지 않습니다.\n"
        send_proto_message(client,error_message)

    else:
        room_id = client.room_id
        notify_room_pmembers(room_id, f"[{client.nickname}]님이 퇴장했습니다.\n", client.sock)
        
        room = next((r for r in rooms if r.id == room_id), None)
        if room:
            room.members = [member for member in room.members if member.nickname != client.nickname]
        
        leave_message = f"방제[{rooms[room_id - 1].title}] 대화 방에서 퇴장했습니다.\n"
        send_proto_message(client,leave_message)
        client.room_id = -1

def handle_protobuf_chat(client, cs_chat):
    print('protobuf_chat')
    if client.room_id == -1:
        error_message = "현재 대화방에 들어가 있지 않습니다.\n"
        send_proto_message(client, error_message)

    else:
        for c in clients:
            if c.sock != client.sock and c.room_id == client.room_id:
                message_text = cs_chat.text

                chat_message = pb.SCChat()
                chat_message.member = client.nickname  
                chat_message.text = message_text  

                serialized_chat_message = chat_message.SerializeToString()

                type_message = pb.Type()
                type_message.type = pb.Type.MessageType.SC_CHAT

                serialized_type_message = type_message.SerializeToString()

                length_prefix_type = len(serialized_type_message).to_bytes(2, byteorder='big')
                length_prefix_chat = len(serialized_chat_message).to_bytes(2, byteorder='big')

                c.sock.sendall(length_prefix_type + serialized_type_message + length_prefix_chat + serialized_chat_message)

def handle_protobuf_shutdown(client):
    global quit_flag
    quit_flag=True

protobuf_handlers = {
    pb.Type.MessageType.CS_NAME: handle_protobuf_name,
    pb.Type.MessageType.CS_ROOMS: handle_protobuf_rooms,
    pb.Type.MessageType.CS_CREATE_ROOM: handle_protobuf_create_room,
    pb.Type.MessageType.CS_JOIN_ROOM: handle_protobuf_join_room,
    pb.Type.MessageType.CS_LEAVE_ROOM: handle_protobuf_leave_room,
    pb.Type.MessageType.CS_CHAT: handle_protobuf_chat,
    pb.Type.MessageType. CS_SHUTDOWN: handle_protobuf_shutdown
}

def process_message(client, buffer):
    print('process_message')
    global type
    try:
        if len(buffer) < 2:
            return
        
        current_message_len = int.from_bytes(buffer[:2], byteorder='big')
        if len(buffer) < current_message_len + 2:
            return  

        message_data = buffer[2:current_message_len + 2]
        
        # JSON 메시지 처리
        if(type=='json'):
            command_json = json.loads(message_data.decode('utf-8'))
            message_type = command_json['type']

            if message_type in message_handlers:
                message_handlers[message_type](client, command_json)

        else:
            try:
                if(client.num%2==0):
                    type_message = pb.Type()
                    type_message.ParseFromString(message_data)
                    client.ptype=type_message.type
                    client.num+=1
                    print('num',client.num)
                    
                # Protobuf 메시지 타입 핸들링
                elif client.ptype in protobuf_handlers:
                    print('client.ptype',client.ptype)
                    protobuf_message = None
                    if client.ptype == pb.Type.MessageType.CS_NAME:
                        protobuf_message = pb.CSName()
                    elif client.ptype == pb.Type.MessageType.CS_CREATE_ROOM:
                        protobuf_message = pb.CSCreateRoom()
                    elif client.ptype == pb.Type.MessageType.CS_JOIN_ROOM:
                        protobuf_message = pb.CSJoinRoom()
                    elif client.ptype == pb.Type.MessageType.CS_CHAT:
                        protobuf_message=pb.CSChat()
                    elif client.ptype == pb.Type.MessageType.CS_LEAVE_ROOM:
                        protobuf_message = None 
                    elif client.ptype == pb.Type.MessageType.CS_ROOMS:
                        protobuf_message= None 
                    elif client.ptype==pb.Type.MessageType.CS_SHUTDOWN:
                        protobuf_message=None

                    if protobuf_message:
                        print('protobuf_message',protobuf_message)
                        protobuf_message.ParseFromString(message_data)
                        protobuf_handlers[client.ptype](client, protobuf_message)
                        client.num = 0
                    else:
                        protobuf_handlers[client.ptype](client)
                        client.num=0

            except Exception as e:
                print(f"Error processing Protobuf message: {e}")

    except Exception as e:
        print(f"Error processing message: {e}")

    return

def handle_client(): 
    print('handle_client')
    global quit_flag
    buffer=b''

    while not quit_flag:
        with condition:
            while client_queue.empty():
                condition.wait()  
            client = client_queue.get() 
            print('client',client) 
            client_queue.task_done()  

        while not quit_flag:
            buffer=client.sock.recv(BUFFER_SIZE)
            print('buffer',client.nickname,buffer)
            if not buffer:
                print(f"NO BUFFER")
                break
            process_message(client,buffer)

    for client in clients:
        print(f"Closing connection for {client.nickname}")
        client.sock.close()  
    clients.clear()   

def server_loop(passive_sock):
    global quit_flag
    print("Waiting for connections...")
    
    while not quit_flag:
        read_sockets, _, _ = select.select([passive_sock], [], [])
        print('read_sockets', read_sockets)

        if read_sockets:
            client_sock, address = passive_sock.accept()
            print(f"Accepted connection from {address}")

            new_client = Client(client_sock, address)
            print('new_client',new_client)
            clients.append(new_client)

            with lock:
                    client_queue.put(new_client)  
                    condition.notify()  

def main(max_workers,format):
    global type
    type=format
    print('Server starting')
    print('Max workers:', max_workers)
    print('type',type)

    passive_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    passive_sock.bind(('127.0.0.1', 10133))
    passive_sock.listen(10)
    
    threads = []
    for _ in range(max_workers):
        thread = threading.Thread(target=server_loop, args=(passive_sock,))
        thread.start()
        threads.append(thread)
        print('threads',thread)

    for _ in range(max_workers):
        thread = threading.Thread(target=handle_client, args=())
        thread.start()
        threads.append(thread)
        print('threads',thread)

    for thread in threads:
        if thread.is_alive():  
            thread.join()
            
    print('passive_sock closed')
    passive_sock.close()
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='서버의 워커 쓰레드 수를 설정합니다.')
    parser.add_argument('--workers', type=int, default=5, help='워커 쓰레드 수 (기본값: 5)')
    parser.add_argument('--format', choices=['json', 'protobuf'], default='json', help='데이터 포맷 (기본값: json)')

    args = parser.parse_args()

    main(args.workers,args.format)

