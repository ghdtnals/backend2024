class Client:
    def __init__(self, sock, address):
        self.sock = sock
        self.nickname = f"({address[0]}, {address[1]})"
        self.room_id = -1
        self.num=0
        self.ptype=None   

class Room:
    def __init__(self, room_id, title):
        self.id = room_id
        self.title = title
        self.members = []
