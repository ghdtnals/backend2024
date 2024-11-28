from http import HTTPStatus
import random
import requests
import urllib
from flask_sqlalchemy import SQLAlchemy
from flask import abort, Flask, make_response, render_template, redirect, request, jsonify

# Flask 앱 및 SQLAlchemy 설정
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqldb://root:root@172.31.139.120:50133/memo'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 네이버 API 설정
naver_client_id = 'qu69Z1tjye1CEAWJOO8r'
naver_client_secret = 'VcUk6tqOqj'
naver_redirect_uri = 'http://mylb-2073667919.ap-northeast-2.elb.amazonaws.com/memo/auth'
NAVER_TOKEN_URL = 'https://nid.naver.com/oauth2.0/token'
NAVER_PROFILE_URL = 'https://openapi.naver.com/v1/nid/me'

# 데이터베이스 모델
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    naver_id = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)

class Memo(db.Model):
    __tablename__ = 'memos'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)

# 데이터베이스 초기화 함수
def init_db():
    with app.app_context():
        db.create_all()

init_db()

@app.route('/')
def home():
    # HTTP 세션 쿠키를 통해 이전에 로그인 한 적이 있는지를 확인한다.
    # 이 부분이 동작하기 위해서는 OAuth 에서 access token 을 얻어낸 뒤
    # user profile REST api 를 통해 유저 정보를 얻어낸 뒤 'userId' 라는 cookie 를 지정해야 된다.
    userId = request.cookies.get('userId', default=None)
    name = None

    # userId 로부터 DB 에서 사용자 이름을 얻어오는 코드를 여기에 작성해야 함
    if userId:
        user = User.query.filter_by(id=userId).first()
        if user:
            name = user.name

    ####################################################

    # 이제 클라에게 전송해 줄 index.html 을 생성한다.
    # template 로부터 받아와서 name 변수 값만 교체해준다.
    return render_template('index.html', name=name)


# 로그인 버튼을 누른 경우 이 API 를 호출한다.
# 브라우저가 호출할 URL 을 index.html 에 하드코딩하지 않고,
# 아래처럼 서버가 주는 URL 로 redirect 하는 것으로 처리한다.
# 이는 CORS (Cross-origin Resource Sharing) 처리에 도움이 되기도 한다.
@app.route('/login')
def onLogin():
    params={
            'response_type': 'code',
            'client_id': naver_client_id,
            'redirect_uri': naver_redirect_uri,
            'state': random.randint(0, 10000)
        }
    urlencoded = urllib.parse.urlencode(params)
    url = f'https://nid.naver.com/oauth2.0/authorize?{urlencoded}'
    return redirect(url)

# 아래는 Authorization code 가 발급된 뒤 Redirect URI 를 통해 호출된다.
@app.route('/auth')
def onOAuthAuthorizationCodeRedirected():
    # 1. redirect uri 를 호출한 request 로부터 authorization code 와 state 정보를 얻어낸다.
    auth_code = request.args.get('code')
    state = request.args.get('state')

    # 2. authorization code 로부터 access token 을 얻어내는 네이버 API 를 호출한다.
    token_params = {
            'grant_type': 'authorization_code',
            'client_id': naver_client_id,
            'client_secret': naver_client_secret,
            'code': auth_code,
            'state': state
        }
    token_response = requests.post(NAVER_TOKEN_URL, params=token_params)
    if token_response.status_code != 200:
        return "Failed to obtain access token", 400

    access_token = token_response.json().get('access_token')

    # 3. 얻어낸 access token 을 이용해서 프로필 정보를 반환하는 API 를 호출하고,
    #    유저의 고유 식별 번호를 얻어낸다.
    headers = {'Authorization': f'Bearer {access_token}'}
    profile_response = requests.get(NAVER_PROFILE_URL, headers=headers)
    if profile_response.status_code != 200:
        return "Failed to retrieve profile", 400

    profile_data = profile_response.json()
    user_id = profile_data['response']['id']  
    user_name = profile_data['response']['name']  

    # 4. 얻어낸 user id 와 name 을 DB 에 저장한다.
     # 데이터베이스에 유저 저장
    user = User.query.filter_by(naver_id=user_id).first()
    if not user:
        user = User(naver_id=user_id, name=user_name)
        db.session.add(user)
        db.session.commit()

    # 5. 첫 페이지로 redirect 하는데 로그인 쿠키를 설정하고 보내준다.
    #    user_id 쿠키는 "dkmoon" 처럼 정말 user id 를 바로 집어 넣는 것이 아니다.
    #    그렇게 바로 user id 를 보낼 경우 정보가 노출되기 때문이다.
    #    대신 user_id cookie map 을 두고, random string -> user_id 형태로 맵핑을 관리한다.
    #      예: user_id_map = {}
    #          key = random string 으로 얻어낸 a1f22bc347ba3 이런 문자열
    #          user_id_map[key] = real_user_id
    #          user_id = key
    # response = redirect('/')
    # response.set_cookie('userId', user_id)
    # return response
    response = make_response(redirect('/'))
    response.set_cookie('userId', str(user.id))
    return response


@app.route('/memo', methods=['GET'])
def get_memos():
    # 로그인이 안되어 있다면 로그인 하도록 첫 페이지로 redirect 해준다.
    userId = request.cookies.get('userId', default=None)
    if not userId:
        return redirect('/')

    #DB 에서 해당 userId 의 메모들을 읽어오도록 아래를 수정한다.
    memos = Memo.query.filter_by(user_id=userId).all()
    memo_list = [{'text': memo.content} for memo in memos]

    return jsonify({'memos': memo_list})


@app.route('/memo', methods=['POST'])
def post_new_memo():
    # 로그인이 안되어 있다면 로그인 하도록 첫 페이지로 redirect 해준다.
    userId = request.cookies.get('userId', default=None)
    if not userId:
        return redirect('/')

    # 클라이언트로부터 JSON 을 받았어야 한다.
    if not request.is_json:
        abort(HTTPStatus.BAD_REQUEST)
    
    data = request.get_json()
    content = data.get('text')

    # TODO: 클라이언트로부터 받은 JSON 에서 메모 내용을 추출한 후 DB에 userId 의 메모로 추가한다.
    new_memo = Memo(user_id=userId, content=content)
    db.session.add(new_memo)
    db.session.commit()

    return '', HTTPStatus.OK


if __name__ == '__main__':
    app.run('0.0.0.0', port=10133, debug=True)
