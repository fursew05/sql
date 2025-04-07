from flask import Flask, render_template, request, redirect, session
from database import MyDB
from dotenv import load_dotenv
import os
import pandas as pd
#.env 로드
load_dotenv()

#Flask 클래스 생성
#생성자 함수에는 파일의 이름을 넣어준다
app = Flask(__name__)

#세션을 사용하기 위해 secret_key를 설정
app.secret_key = os.getenv('secret_key')

#DB server에 웹에서 사용할 테이블이 존재하는가?
#존재한다면 아무 행동도 하지 않는다
#존재 하지 않으면 테이블 생성(IF NOT EXIST 구문 사용)

# 유저 테이블 생성
create_table = """
    CREATE TABLE
    IF NOT EXISTS
    `user_list`
 (
    `id` varchar(32) primary key,
    `password` varchar(64) not null,
    `name` varchar(32)
    )
"""
# MyDB를 이용하여 서버 접속 + 쿼리문 넣기
web_db = MyDB()

#create_table 쿼리문 실행
web_db.execute_query(create_table)

#유저와 서버간의 데이터를 주고 받는 부분 생성
#api 생성

#localhost:5000/ 요청이 들어왔을 때
@app.route('/')
def index():
    #로그인 화면을 보여준다
    return render_template('signin.html')

@app.route('/login',methods=['post'])
def login():
    #post 방식으로 보낸 데이터는 request 안에 form에 존재(딕셔너리 형태)
    #유저가 보낸 id값을 변수에 저장
    input_id = request.form['user_id']
    input_pass = request.form['user_pass']
    #유저가 보낸 데이터를 확인
    print(f"[post]/login : {input_id},{input_pass}")

    #로그인
    #user_list table에서 유저가 보낸 id, password를 모두 존재하는 인덱스가 있는가?
    # sql 쿼리문 : select문
    login_query = """
    SELECT *
    FROM `user_list`
    WHERE `id` = %s and `password` = %s 
    """

    #execute_query() 함수는 select문을 넣었을때 돌려주는 데이터의 타입은 데이터프레임
    #데이터프레임의 길이가 0이면 로그인 실패
    #길이가 1이라면 로그인 성공
    res_sql = web_db.execute_query(login_query,input_id,input_pass)
    print(res_sql)
    if len(res_sql):
        #로그인이 성공했다면 특정 페이지를 보여준다(render_template(file_name))
        #로그인이 성공했다면 특정 주소로 이동한다(redirect(주소값))
        #main.html과 같이 로그인을 한 유저의 이름을 보낸다
        #res_sql.loc[0,'name'], res_sql.iloc[0,2],res_sql['name'][0]
        logined_name = res_sql.loc[0,'name']

        #세션에 로그인 정보를 담는다
        session['login_info'] = request.form

        #DataBase에 있는 sales records table 로드
        select_query = """
        SELECT * FROM `sales records` limit 5
        """
        sales_data = web_db.execute_query(select_query)
        #sales_data의 타입은 데이터프레임
        #데이터프레임을 [{},{},...] 형태로 바꿔야함
        list_data = sales_data.to_dict(orient='records')
        #html table에 필요한 데이터를 컬럼의 이름들을 변수에 따로 저장
        #list_data.keys()
        cols = list_data[0].keys()
        
        # sales_data를 df로 copy하기
        df = sales_data.copy()
        # sales_data -> `Sales Channel` 컬럼을 기준으로 그룹화
        group_df = df[['Sales Channel','Total Profit']].groupby('Sales Channel').sum()
        #`Total Profit` 데이터를 그룹화 연산 합계
        # index의 값을 리스트로 생성
        group_list = list(group_df.index)
        # values의 값을 리스트로 생성
        group_values = group_df.values.tolist()
        print(f'인덱스 : {group_list}, 값 : {group_values}')
        #render_template(파일의 이름, key = value, key2 = value2, ...)

        return render_template('main.html', name = logined_name, 
                               columns = cols, td_data = list_data,
                               x_data = group_list, y_data = group_values)
    else :
        #로그인이 실패했다면 로그인 페이지로 돌아간다
        #로그인 주소로 이동한다('/')
        return redirect('/')

#회원가입 페이지를 보여주는 api 생성
@app.route('/signup')
def signup():
    #로그인이 되어있는 상태라면 해당 페이지를 보여주지 않는다
    #로그인이 되어있는 상태 : session에서 login_info 키가 존재하는가?
    if 'login_info' in session:
        return render_template('home.html')
    else:
        return render_template('signup.html')

#실제 회원 데이터를 받아서 DB에 저장하는 api 생성
@app.route('/signup2',methods=['post'])
def signup2():
    #form태그를 이용해서 user가 보낸 데이터 존재
    #id,password,name의 값들을 각각 다른 변수에 저장
    id = request.form['user_id']
    password = request.form['user_pass']
    name = request.form['user_name']
    #변수들을 확인하기 위해 print해보기
    print(f"""user_id : {id}
              user_pass : {password}
              user_name : {name}""")
    #insert query문 생성
    insert_query = """
        INSERT INTO `user_list`
        VALUES (%s, %s, %s)
        """
    #try 구문사용
    #MyDB class에 내장된 execute_query()를 호출
    #회원가입 성공했다면 로그인 페이지로 이동
    #예외발생시 return을 회원가입 실패한 경우로 회원가입 페이지로 이동
    try :
        web_db.execute_query(insert_query,id,password,name,inplace=True)
        return redirect('/')
    except Exception as e:
        print(e)
        return redirect('/signup')
@app.route('/graph')
def graph():
    #select 쿼리문을 이용하여 sales records 전체 데이터를 로드
    select_query = """
    SELECT * FROM `sales records`
    """
    df = web_db.execute_query(select_query)
    #결과 DataFrame에서 Order Date 컬럼의 데이터를 시계열 데이터로 변경하여 저장
    df['Order Date'] = pd.to_datetime(df['Order Date'])
    #새로운 파생변수 Order Year를 생성하여 Order Date에서 4글자의 연도를 추출하여 저장
    df['Order Year'] = df['Order Date'].dt.year
    #sales channel과 order year를 기준으로 그룹화 total_profit의 합계를 구해준다
    group_df = df[['Sales Channel','Order Year','Total Profit']].groupby(['Sales Channel','Order Year']).sum()
    #online 데이터를 따로 추출
    online_group = group_df.loc['Online']
    #offline 데이터를 따로 추출
    offline_group = group_df.loc['Offline']
    #online 데이터를 추출한 곳에서 인덱스의 값을 리스트로 생성
    index = list(online_group.index)
    #online 데이터의 value들을 리스트로 생성
    online_values = online_group.values.tolist()
    #offline 데이터를 추출한 곳에서 인덱스의 값을 리스트로 생성
    #offline 데이터의 value들을 리스트로 생성
    offline_values = offline_group.values.tolist()
    #graph.html 파일에 online, offline 막대그래프를 생성
    return render_template('graph.html',x = index, online_y = online_values,
   offline_y=offline_values)
#웹 서버를 실행
app.run(debug=True)