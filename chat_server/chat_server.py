import socket
import threading
import json
import message_pb2 as pb
import select
import queue
from models import (Client, Room)
clients = []
rooms = []
quit_flag = False
BUFFER_SIZE = 65536

def broadcast_message(message, sender_sock, room_id):
    for client in clients:
        if client.sock != sender_sock and client.room_id == room_id:
            system_message = {
            'type': 'SCSystemMessage',
            'text': message
            }
            send_json_message(client.sock, system_message)

def broadcast_proto_message(message, sender_sock, room_id):
    print('broadcast_proto')
    for client in clients:
        if client.sock != sender_sock and client.room_id == room_id:
            #send_proto_message(client, message)
             client.add_message((send_proto_message, message))  # 함수와 메시지를 튜플로 추가

def notify_room_members(room_id, message, exclude_sock=None):
    for room in rooms:
        if room.id == room_id:
            for member in room.members:
                if member.sock != exclude_sock:
                    system_message = {
                    'type': 'SCSystemMessage',
                    'text': message
                    }
                    send_json_message(member.sock, system_message)

def notify_room_pmembers(room_id, message, exclude_sock=None):
    for room in rooms:
        if room.id == room_id:
            for member in room.members:
                if member.sock != exclude_sock:
                    #send_proto_message(member, message)
                    member.add_message((send_proto_message, message))

def handle_name(client, command_json):
    new_nickname = command_json['name']
    client.nickname = new_nickname
    system_message = {
        'type': 'SCSystemMessage',
        'text': f"이름이 {new_nickname}으로 변경되었습니다.\n"
    }
    send_json_message(client.sock, system_message)

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

    send_json_message(client.sock, rooms_message)    

def handle_create_room(client, command_json):
    if client.room_id != -1:
        error_message = {
        'type': 'SCSystemMessage',
        'text': f"대화 방에 있을 때는 방을 개설할 수 없습니다.\n"
    }
        send_json_message(client.sock, error_message)
        return
        
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
    send_json_message(client.sock, system_message)

def handle_join_room(client, command_json):
    room_id = command_json['roomId']

    if client.room_id != -1:
        error_message = {
            'type': 'SCSystemMessage',
            'text': "대화 방에 있을 때는 다른 방에 들어갈 수 없습니다.\n"
        }
        send_json_message(client.sock, error_message)
        return  

    room = next((r for r in rooms if r.id == room_id), None)
    
    if room is None:  
        error_message = {
            'type': 'SCSystemMessage',
            'text': "대화방이 존재하지 않습니다.\n"
        }
        send_json_message(client.sock, error_message)
        return 

    room.members.append(client)
    client.room_id = room_id
    success_message = {
        'type': 'SCSystemMessage',
        'text': f"방제[{room.title}] 방에 입장했습니다.\n"
    }
    send_json_message(client.sock, success_message)
    notify_room_members(client.room_id, f"[{client.nickname}]님이 입장했습니다.\n")


def handle_leave_room(client,command_json):
    if client.room_id == -1:
        error_message = {
        'type': 'SCSystemMessage',
        'text': f"현재 대화방에 들어가 있지 않습니다.\n"
    }
        send_json_message(client.sock, error_message)

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
        send_json_message(client.sock, system_message)
        client.room_id = -1

def handle_shutdown(client):
    global quit_flag
    quit_flag = True

    shutdown_message = "서버가 종료됩니다.\n"
    system_message = {
        'type': 'SCSystemMessage',
        'text': shutdown_message
    }

    print("모든 클라이언트에게 종료 메시지를 보냈습니다.")

def send_json_message(sock, message):
    serialized = json.dumps(message).encode('utf-8') 
    length_prefix = len(serialized).to_bytes(2, byteorder='big')  
    sock.sendall(length_prefix + serialized) 

# 핸들러 맵
message_handlers = {
    'CSName': handle_name,
    'CSRooms': handle_rooms,
    'CSCreateRoom': handle_create_room,
    'CSJoinRoom': handle_join_room,
    'CSLeaveRoom': handle_leave_room,
    'CSShutdown': handle_shutdown,
}

def handle_protobuf_name(client, cs_name):
        print('handle_proto_name')
        new_nickname = cs_name.name
        print('cs_name.name',cs_name.name)
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
    # 클라이언트가 채팅 메시지를 보냈을 때 처리하는 함수
    if client.room_id == -1:
        # 대화 방에 없을 경우 시스템 메시지 전송
        error_message = "현재 대화방에 들어가 있지 않습니다.\n"
        send_proto_message(client, error_message)
    else:
        # 대화 방에 있는 경우, 메시지를 다른 클라이언트에게 전송
        message_text = cs_chat.text
        print('message_text',message_text)
        broadcast_proto_message(f"[{client.nickname}]님이: {message_text}", client.sock, client.room_id)

def handle_protobuf_shutdown(client):
    global quit_flag
    quit_flag = True

    shutdown_message = "서버가 종료됩니다.\n"
    
    # 모든 클라이언트에게 종료 메시지 전송
    for c in clients:
        c.add_message(shutdown_message) 
        c.add_message(None)  

    print("모든 클라이언트에게 종료 메시지를 보냈습니다.")

    # 모든 클라이언트의 스레드가 종료될 때까지 대기
    for c in clients:
        c.thread.join()  # 각 클라이언트의 메시지 처리 스레드 종료 대기

    print("모든 클라이언트의 스레드가 종료되었습니다.")
   


def send_proto_message(client, message):
    system_message = pb.SCSystemMessage()
    system_message.text = message

    serialized_system_message = system_message.SerializeToString()

    type_message = pb.Type()
    type_message.type = pb.Type.MessageType.SC_SYSTEM_MESSAGE

    serialized_type_message = type_message.SerializeToString()

    length_prefix_type = len(serialized_type_message).to_bytes(2, byteorder='big')
    length_prefix_system = len(serialized_system_message).to_bytes(2, byteorder='big')
    client.sock.sendall(length_prefix_type + serialized_type_message + length_prefix_system + serialized_system_message)

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
    try:
        if len(buffer) < 2:
            return
        
        current_message_len = int.from_bytes(buffer[:2], byteorder='big')
        if len(buffer) < current_message_len + 2:
            return  

        message_data = buffer[2:current_message_len + 2]
        
        # JSON 메시지 처리
        try:
            command_json = json.loads(message_data.decode('utf-8'))
            message_type = command_json['type']

            if message_type in message_handlers:
                message_handlers[message_type](client, command_json)

        except json.JSONDecodeError:
            # JSON 파싱 실패 시 Protobuf 처리
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

def handle_client(client):
    
    print('handle_client')
    buffer=b''
    while not quit_flag:
        print('quit_flag')
        try:
            buffer=client.sock.recv(BUFFER_SIZE)
            print('buffer',buffer)
            if not buffer:
                print(f"Client {client.nickname} disconnected.")
                break  
            process_message(client,buffer)

        except Exception as e:
            print(f"Error handling client {client.nickname}: {e}")
            break 

    if client in clients:  
        clients.remove(client)
    client.sock.close()
    print(f"Client disconnected: {client.nickname}")

def main():
    passive_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    passive_sock.bind(('127.0.0.1', 10133))
    passive_sock.listen(10)

    print("Waiting for connections...")

    sockets_list = [passive_sock]

    while not quit_flag:
        read_sockets, _, _ = select.select(sockets_list, [], [])

        for notified_sock in read_sockets:
            print('read_sockets',read_sockets)
            if notified_sock == passive_sock:
                print('notified_sock',notified_sock)
                # 새로운 클라이언트 연결 수락
                client_sock, address = passive_sock.accept()
                print(f"Accepted connection from {address}")
            
                new_client = Client(client_sock, address)
                #print(new_client.sock,new_client.nickname)
                clients.append(new_client)
                #sockets_list.append(client_sock)  
                client_thread = threading.Thread(target=handle_client, args=(new_client,))
                client_thread.start()


            else:
                # 클라이언트로부터 메시지 수신
                client = next((c for c in clients if c.sock == notified_sock), None)

                if client:
                    buffer = notified_sock.recv(BUFFER_SIZE)
                    print('buffer2',buffer)
                    if not buffer:
                        clients.remove(client)
                        sockets_list.remove(notified_sock)
                        notified_sock.close()
                        print(f"Client disconnected: {client.nickname}")
                        continue

                    process_message(client, buffer)

    passive_sock.close()
    print("서버가 종료되었습니다.")

if __name__ == "__main__":
    main()

