import queue
import threading

class Client:
    def __init__(self, sock, address):
        self.sock = sock
        self.nickname = f"({address[0]}, {address[1]})"
        self.room_id = -1
        self.num=0
        self.ptype=None
        

        self.message_queue = queue.Queue()  # 클라이언트 메시지 큐
        self.condition = threading.Condition()  # Condition Variable
        self.lock = threading.Lock()  # Mutex 
        self.thread = threading.Thread(target=self.process_messages) # 메시지 처리 쓰레드
        self.thread.start() 
        self.should_exit=False
        
    def process_messages(self):
        while True:
            with self.condition: 
                while self.message_queue.empty(): 
                    self.condition.wait()  

                message = self.message_queue.get()  
                if message is None:  
                    break

            with self.lock:  
                if isinstance(message, tuple):
                    func, msg = message  
                    func(self, msg)  
                else:
                    self.handle_message(message)

    def add_message(self, message):
        with self.lock:  
            self.message_queue.put(message) 
            with self.condition: 
                self.condition.notify()

    def handle_message(self, message):
        print(f"Processing message from {self.nickname}: {message}")

class Room:
    def __init__(self, room_id, title):
        self.id = room_id
        self.title = title
        self.members = []
