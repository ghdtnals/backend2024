import json
import sys

def main(argv):

    obj1 = {
    'name': 'MJ Kim',
    'id': 12345678,
     'work': {
       'name': 'Myongji Unviversity',
       'address': '116 Myongji-ro'
        },
       'scores':[100,90.5,80.0]
    }

    obj2 = {
    'phone': '010-0000-0000',
    'age': 20,
    }

    obj = [obj1, obj2]
    s = json.dumps(obj)
    
    print(s)
    print('Type', type(s).__name__)

if __name__ == '__main__':
 main(sys.argv)