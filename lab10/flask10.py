from flask import Flask
from flask import request,jsonify,make_response

app = Flask(__name__)

@app.route('/<int:arg1>/<op>/<int:arg2>', methods=['GET'])
def get_method(arg1,op,arg2):

  if op not in ['+','-','*']:
   return make_response(jsonify(error="지원하지 않는 연산자입니다."),400)
 
  else:
   if(op=='+'):
      result=arg1+arg2
   elif(op=='-'):
      result=arg1-arg2
   else:
      result=arg1*arg2 

   return make_response(jsonify(result=result),200)
 
@app.route('/', methods=['POST'])
def post_method():
 data = request.get_json()

 if not data or 'arg1' not in data or 'arg2' not in data or 'op' not in data:
        return make_response(jsonify(error="필수 데이터가 누락되었습니다."), 400)
 
 arg1 = data['arg1']
 arg2 = data['arg2']
 op = data['op']

 if op not in ['+', '-', '*']:
   return make_response(jsonify(error="지원하지 않는 연산자입니다."), 400)
 
 else:
   if op == '+':
      result = arg1 + arg2
   elif op == '-':
      result = arg1 - arg2
   else:
      result = arg1 * arg2

   return make_response(jsonify(result=result),200)

if __name__ == '__main__':
 app.run(host='0.0.0.0', port=20133)