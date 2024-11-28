# Memo 서비스 구현 및 AWS 배포

이 프로젝트는 Flask를 이용한 간단한 메모 서비스입니다. 사용자는 네이버 OAuth를 통해 로그인하고, 로그인 후 메모를 생성하고 조회할 수 있습니다. 서비스는 MySQL 데이터베이스를 사용하며, AWS 환경에서 Application Load Balancer(ALB)를 사용해 배포됩니다.

## AWS 실행 환경

   2대의 독립된 EC2 인스턴스(mjubackend)에 memo.py 코드가 올라가 실행되고 있습니다. 데이터베이스는 internal 서브넷에 있는 EC2 인스턴스(db)에 docker를 이용해 MYSQL을 실행하였습니다. 

   ### 실행 흐름과 원리
   1. http://lb DNS이름/memo로 접속
   2. loadbalancer가 80번 포트로 들어오는 연결을 8000번 포트로 변환
   3. Nginx는 8000번 포트로 들어오는 url에 따라 행동을 특정하는데 본 환경에서는 /memo라는 경로가 들어오면 127.0.0.1:30001 를 통해서 Uwsgi를 호출
   4. Uwsgi는 /memo 경로에 대해서 memo.py 호출하는데 /memo prefix 제거 후 memo.py 호출
   최종적으로 http://mylb-2073667919.ap-northeast-2.elb.amazonaws.com/memo/ 의 요청이 memo.py의 @app.route('/')로 전달되게 됩니다. 

## memo.py 코드 설명

### 주요 라이브러리

   - Flask: 웹 서버 프레임워크.
   - SQLAlchemy: ORM을 이용한 데이터베이스 관리.
   - requests: 네이버 OAuth와 API 통신을 위해 사용.

### 1. Flask 앱 설정

   Flask 애플리케이션을 설정하고, MySQL 데이터베이스에 연결합니다.
   SQLALCHEMY_DATABASE_URI는 DB 연결 URI로 AWS EC2에 호스팅된 MySQL 데이터베이스의 private IP에 연결합니다.

### 2. 데이터베이스 모델

   User 모델은 네이버 로그인 후 저장되는 사용자 정보를 다룹니다.
   Memo 모델은 사용자의 메모 내용을 저장하는 테이블입니다.

### 3. OAuth 인증 (네이버 로그인)

   사용자가 로그인 버튼을 클릭하면, 네이버 OAuth 인증 페이지로 리디렉션됩니다.
   인증 후, 네이버에서 제공하는 Authorization Code를 통해 Access Token을 얻고, 이를 이용해 사용자의 정보를 가져옵니다.

### 4. 메모 조회 및 추가

   GET /memo: 로그인한 사용자의 메모를 조회합니다.
   POST /memo: 새로운 메모를 작성하고 DB에 저장합니다.






