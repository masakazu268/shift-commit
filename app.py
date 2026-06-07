# import os
# import random
# import io
# from datetime import datetime, timedelta
# from flask import Flask, render_template, request, send_file , url_for # pyright: ignore[reportMissingImports]
# import pandas as pd
# import mimetypes
# import os
# import openpyxl # pyright: ignore[reportMissingModuleSource]


# app = Flask(__name__)

# mimetypes.add_type('application/vnd.ms-excel.sheet.macroEnabled.12', '.xlsm')

# # --- [ロジック部分] 既存のコードをそのまま活用 ---
# def is_weekend_or_holiday(date, holidays):
#     return date.weekday() >= 5 or date.strftime('%Y-%m-%d') in holidays

# def check_employee_holidays(employee_holidays, required_holidays):
#     for employee, holidays in employee_holidays.items():
#         if holidays < required_holidays.get(employee, 0):
#             return False
#     return True

# # --- [ロジック部分] 減点方式（ペナルティスコア）アルゴリズム ---

# def calculate_total_penalty(shift_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict):
#     """
#     完成した1ヶ月分のシフト表を採点する関数（点数が低いほど優秀）
#     """
#     total_penalty = 0
#     num_days = len(date_list)
    
#     # --- 1. 日ごとのチェック（人数不足のチェック） ---
#     for i, date in enumerate(date_list):
#         date_str = date.strftime('%Y-%m-%d')
        
#         if date_str in holidays:
#             required_workers = 5
#         elif date.weekday() in [5, 6]:  # 土日
#             required_workers = 6
#         else:
#             required_workers = 11
            
#         # その日に実際に仕事が割り当てられている人数をカウント
#         working_count = 0
#         for employee in shift_table:
#             task = shift_table[employee][i]
#             if task not in ['', 'RH', 'NG']:
#                 working_count += 1
                
#         # 人数が足りない場合は大きなペナルティ（1人不足ごとに1000点）
#         if working_count < required_workers:
#             shortage = required_workers - working_count
#             total_penalty += shortage * 1000

#     # --- 2. 社員ごとのチェック（連勤、希望休、総公休数のチェック） ---
#     for employee, shifts in shift_table.items():
#         consecutive_work = 0
#         actual_holidays = 0
        
#         for i, task in enumerate(shifts):
#             date_str = date_list[i].strftime('%Y-%m-%d')
            
#             # 【希望休チェック】希望休なのに出勤(NGなど)になっていたらペナルティ
#             if employee in hope_holidays_dict and date_str in hope_holidays_dict[employee]:
#                 if task == 'NG' or (task not in ['', 'RH']):
#                     total_penalty += 500
            
#             # 【夜勤明けチェック】前日がM05なのに、今日出勤していたらペナルティ
#             if i > 0 and shifts[i-1] == 'M05':
#                 if task != '':
#                     total_penalty += 80

#             # 【連勤チェック】
#             if task not in ['', 'RH']:
#                 consecutive_work += 1
#                 if consecutive_work >= 6:  # 6連勤以上はペナルティ
#                     total_penalty += 100
#             else:
#                 consecutive_work = 0
#                 actual_holidays += 1
                
#         # 【総公休数チェック】目標の公休数より少なかったらペナルティ
#         target_holidays = required_holidays.get(employee, 0)
#         if actual_holidays < target_holidays:
#             shortage_days = target_holidays - actual_holidays
#             total_penalty += shortage_days * 50

#     return total_penalty



# def generate_single_candidate(employee_capabilities, date_list, holidays, hope_holidays_dict):
#     """
#     とりあえずルールを無視してでも、1パターンのシフトを最後まで作りきる関数
#     """
#     shift_table = {employee: [] for employee in employee_capabilities}
#     consecutive_work_days = {employee: 0 for employee in employee_capabilities}
    
#     for i, date in enumerate(date_list):
#         date_str = date.strftime('%Y-%m-%d')

#         if date_str in holidays:
#             required_workers = 5
#             possible_tasks = ['M01','M02', 'M03', 'M04', 'M05']
#         elif date.weekday() in [5, 6]:
#             required_workers = 6
#             possible_tasks = ['M01', 'HM' , 'M02', 'M03', 'M04', 'M05']
#         else:
#             required_workers = 11
#             possible_tasks = ['771', '772', '773', '774', '775', '776', '777', 'M01', 'M02', 'M04', 'M05']

#         day_tasks = set()
#         employees = list(employee_capabilities.keys())
#         random.shuffle(employees)

#         for employee in employees:
#             # 夜勤(M05)の翌日は一応休みを優先的に入れる
#             if i > 0 and shift_table[employee][i-1] == 'M05':
#                 shift_table[employee].append('')
#                 consecutive_work_days[employee] = 0
#                 continue

#             # 希望休の処理
#             if employee in hope_holidays_dict and date_str in hope_holidays_dict[employee]:
#                 shift_table[employee].append('RH')
#                 consecutive_work_days[employee] = 0
#             # 人数が足りない ＆ 連勤が詰まってなければ出勤
#             elif len(day_tasks) < required_workers and consecutive_work_days[employee] < 5:
#                 possible_employee_tasks = [task for task in employee_capabilities[employee] if task in possible_tasks and task not in day_tasks]
#                 if possible_employee_tasks:
#                     task = random.choice(possible_employee_tasks)
#                     shift_table[employee].append(task)
#                     day_tasks.add(task)
#                     consecutive_work_days[employee] += 1
#                 else:
#                     shift_table[employee].append('')
#                     consecutive_work_days[employee] = 0
#             else:
#                 shift_table[employee].append('')
#                 consecutive_work_days[employee] = 0

#         # 人数がどうしても足りなかった日のバックアップ処理
#         if len(day_tasks) < required_workers:
#             for employee in shift_table.keys():
#                 if date_str in hope_holidays_dict.get(employee, []):
#                     # 本来はRHだが、どうしても出勤させる場合はNGマークにする
#                     if shift_table[employee][-1] == 'RH':
#                         shift_table[employee][-1] = 'NG'

#     return shift_table


# def generate_shift_table(employee_capabilities, start_date, num_days, holidays, required_holidays, hope_holidays, num_candidates=20):
#     """
#     複数のシフト候補を作り、最もペナルティが低い（優秀な）シフトを返却するメイン関数
#     """
#     date_list = [start_date + timedelta(days=i) for i in range(num_days)]

#     # 希望休の辞書化
#     hope_holidays_dict = {}
#     for employee, day in hope_holidays:
#         if employee not in hope_holidays_dict:
#             hope_holidays_dict[employee] = []
#         hope_holidays_dict[employee].append((start_date + timedelta(days=day - 1)).strftime('%Y-%m-%d'))

#     best_shift_table = None
#     best_penalty = float('inf')  # 初期値は無限大

#     # Renderのタイムアウト（30秒）に余裕で間に合うよう、20パターンほど生成して比較
#     for _ in range(num_candidates):
#         candidate_table = generate_single_candidate(employee_capabilities, date_list, holidays, hope_holidays_dict)
        
#         # この候補の不満度（ペナルティ）を計算
#         penalty = calculate_total_penalty(
#             candidate_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict
#         )
        
#         # もし過去最高のクオリティ（最も低いペナルティ）なら、正解候補としてキープ
#         if penalty < best_penalty:
#             best_penalty = penalty
#             best_shift_table = candidate_table
            
#         # 完璧なシフト（0点）が見つかったらその時点で終了
#         if best_penalty == 0:
#             break

#     print(f"🎉 採用されたシフトのペナルティスコア: {best_penalty}点")
#     return best_shift_table

# DEFAULT_CAPABILITIES = "A,773,774,775,M01,HM,M05; B,773,774,776,777,M01,HM,M02,M03,M05; C,773,774,776,777,M03; D,773,774,776,777,M02,M03,M05; E,773,774,775,HM; F,776,777,M02,M03; G,771,772,775,M04; H,771,772,773,774,775,M01,HM,M04,M05; I,771,772,773,774,M01h,M01,HM,M04,M05; J,772,773,775,HM; K,771,774,776,777,M01,M03,HM; L,M02; M,771,772,774,M01,HM,M04; N,771,772"
# DEFAULT_REQUIREMENTS = "A,8; B,8; C,8; D,8; E,8; F,8; G,8; H,8; I,8; J,8; K,8; L,8; M,8; N,8"

# @app.route('/', methods=['GET'])
# def index():
#     # 入力画面を表示
#     return render_template('index.html', default_caps=DEFAULT_CAPABILITIES, default_reqs=DEFAULT_REQUIREMENTS)

# @app.route('/generate', methods=['POST'])
# def generate():
#     try:
#         # フォームからのデータ受け取り
#         start_date_str = request.form.get('start_date')
#         start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
#         num_days = int(request.form.get('num_days'))
        
#         holidays_raw = request.form.get('holidays', '')
#         holidays = [h.strip() for h in holidays_raw.split(',') if h.strip()]
        
#         hope_holidays_raw = request.form.get('hope_holidays', '').split(';')
#         hope_holidays = []
#         for item in hope_holidays_raw:
#             if ',' in item:
#                 employee, day = item.split(',')
#                 hope_holidays.append((employee.strip(), int(day.strip())))

#         # 社員能力と休日要件のパース
#         employee_capabilities = {}
#         employees_raw = request.form.get('employees', '').split(';')
#         for item in employees_raw:
#             if ',' in item:
#                 parts = item.split(',')
#                 employee = parts[0].strip()
#                 skills = [s.strip() for s in parts[1:]]
#                 employee_capabilities[employee] = skills

#         required_holidays = {}
#         holidays_required_raw = request.form.get('holiday_requirements', '').split(';')
#         for item in holidays_required_raw:
#             if ',' in item:
#                 employee, holiday_count = item.split(',')
#                 required_holidays[employee.strip()] = int(holiday_count.strip())

#         # シフト生成
#         shift_table = generate_shift_table(
#             employee_capabilities, start_date, num_days, holidays, required_holidays, hope_holidays
#         )

#         # Pandasのデータフレームを作成
#         df = pd.DataFrame(shift_table)
#         df.index = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(len(list(shift_table.values())[0]))]
#         df_transposed = df.transpose()

#         # サーバーにファイルを保存せず、メモリ上のバッファにExcelを書き出す（Webアプリの鉄板処理）
#         output = io.BytesIO()
#         with pd.ExcelWriter(output, engine='openpyxl') as writer:
#             df_transposed.to_excel(writer, sheet_name='ShiftTable')
#         output.seek(0)

#         # ユーザーにダウンロードさせる
#         filename = f"shift_{start_date_str}.xlsx"
#         return send_file(output, as_attachment=True, download_name=filename, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

#     except Exception as e:
#         return f"エラーが発生しました: {str(e)}", 400

# if __name__ == '__main__':
#     app.run(debug=True)


import os
import random
import io
from datetime import datetime, timedelta
from flask import Flask, render_template, request, send_file, url_for # pyright: ignore[reportMissingImports]
import pandas as pd
import mimetypes
import openpyxl # pyright: ignore[reportMissingModuleSource]
from flask_sqlalchemy import SQLAlchemy # pyright: ignore[reportMissingImports]

app = Flask(__name__)

mimetypes.add_type('application/vnd.ms-excel.sheet.macroEnabled.12', '.xlsm')

# ==========================================
# 🗄️ データベース（Neon / SQLAlchemy）設定
# ==========================================
database_url = os.getenv("DATABASE_URL")

# 本番環境（Render/Neon）用の補正
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# 環境変数が存在する（本番環境など）場合のみデータベースを設定
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)
    
    # 📝 シフト結果を格納するデータベースモデル（テーブル定義）
    class ShiftResult(db.Model):
        __tablename__ = 'shift_results'
        id = db.Column(db.Integer, primary_key=True)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        start_date = db.Column(db.String(10), nullable=False)     # "2026-06-01" など
        employee_name = db.Column(db.String(50), nullable=False)  # "A" などの社員名
        date_str = db.Column(db.String(10), nullable=False)       # "2026-06-01" などの日付
        task = db.Column(db.String(10))                           # "M01" などのシフト記号

    # アプリ起動時にテーブルを自動作成
    with app.app_context():
        db.create_all()
else:
    # ローカル環境で環境変数がない場合は、dbをNoneにしてエラーを防ぐ
    db = None

# --- [ロジック部分] 既存のコードをそのまま活用 ---
def is_weekend_or_holiday(date, holidays):
    return date.weekday() >= 5 or date.strftime('%Y-%m-%d') in holidays

def check_employee_holidays(employee_holidays, required_holidays):
    for employee, holidays in employee_holidays.items():
        if holidays < required_holidays.get(employee, 0):
            return False
    return True

# --- [ロジック部分] 減点方式（ペナルティスコア）アルゴリズム ---
def calculate_total_penalty(shift_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict):
    total_penalty = 0
    num_days = len(date_list)
    
    for i, date in enumerate(date_list):
        date_str = date.strftime('%Y-%m-%d')
        if date_str in holidays:
            required_workers = 5
        elif date.weekday() in [5, 6]:
            required_workers = 6
        else:
            required_workers = 11
            
        working_count = 0
        for employee in shift_table:
            task = shift_table[employee][i]
            if task not in ['', 'RH', 'NG']:
                working_count += 1
                
        if working_count < required_workers:
            shortage = required_workers - working_count
            total_penalty += shortage * 1000

    for employee, shifts in shift_table.items():
        consecutive_work = 0
        actual_holidays = 0
        
        for i, task in enumerate(shifts):
            date_str = date_list[i].strftime('%Y-%m-%d')
            
            if employee in hope_holidays_dict and date_str in hope_holidays_dict[employee]:
                if task == 'NG' or (task not in ['', 'RH']):
                    total_penalty += 500
            
            if i > 0 and shifts[i-1] == 'M05':
                if task != '':
                    total_penalty += 80

            if task not in ['', 'RH']:
                consecutive_work += 1
                if consecutive_work >= 6:
                    total_penalty += 100
            else:
                consecutive_work = 0
                actual_holidays += 1
                
        target_holidays = required_holidays.get(employee, 0)
        if actual_holidays < target_holidays:
            shortage_days = target_holidays - actual_holidays
            total_penalty += shortage_days * 50

    return total_penalty

def generate_single_candidate(employee_capabilities, date_list, holidays, hope_holidays_dict):
    shift_table = {employee: [] for employee in employee_capabilities}
    consecutive_work_days = {employee: 0 for employee in employee_capabilities}
    
    for i, date in enumerate(date_list):
        date_str = date.strftime('%Y-%m-%d')

        if date_str in holidays:
            required_workers = 5
            possible_tasks = ['M01','M02', 'M03', 'M04', 'M05']
        elif date.weekday() in [5, 6]:
            required_workers = 6
            possible_tasks = ['M01', 'HM' , 'M02', 'M03', 'M04', 'M05']
        else:
            required_workers = 11
            possible_tasks = ['771', '772', '773', '774', '775', '776', '777', 'M01', 'M02', 'M04', 'M05']

        day_tasks = set()
        employees = list(employee_capabilities.keys())
        random.shuffle(employees)

        for employee in employees:
            if i > 0 and shift_table[employee][i-1] == 'M05':
                shift_table[employee].append('')
                consecutive_work_days[employee] = 0
                continue

            if employee in hope_holidays_dict and date_str in hope_holidays_dict[employee]:
                shift_table[employee].append('RH')
                consecutive_work_days[employee] = 0
            elif len(day_tasks) < required_workers and consecutive_work_days[employee] < 5:
                possible_employee_tasks = [task for task in employee_capabilities[employee] if task in possible_tasks and task not in day_tasks]
                if possible_employee_tasks:
                    task = random.choice(possible_employee_tasks)
                    shift_table[employee].append(task)
                    day_tasks.add(task)
                    consecutive_work_days[employee] += 1
                else:
                    shift_table[employee].append('')
                    consecutive_work_days[employee] = 0
            else:
                shift_table[employee].append('')
                consecutive_work_days[employee] = 0

        if len(day_tasks) < required_workers:
            for employee in shift_table.keys():
                if date_str in hope_holidays_dict.get(employee, []):
                    if shift_table[employee][-1] == 'RH':
                        shift_table[employee][-1] = 'NG'

    return shift_table

def generate_shift_table(employee_capabilities, start_date, num_days, holidays, required_holidays, hope_holidays, num_candidates=20):
    date_list = [start_date + timedelta(days=i) for i in range(num_days)]

    hope_holidays_dict = {}
    for employee, day in hope_holidays:
        if employee not in hope_holidays_dict:
            hope_holidays_dict[employee] = []
        hope_holidays_dict[employee].append((start_date + timedelta(days=day - 1)).strftime('%Y-%m-%d'))

    best_shift_table = None
    best_penalty = float('inf')

    for _ in range(num_candidates):
        candidate_table = generate_single_candidate(employee_capabilities, date_list, holidays, hope_holidays_dict)
        penalty = calculate_total_penalty(
            candidate_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict
        )
        if penalty < best_penalty:
            best_penalty = penalty
            best_shift_table = candidate_table
            
        if best_penalty == 0:
            break

    print(f"🎉 採用されたシフトのペナルティスコア: {best_penalty}点")
    return best_shift_table

DEFAULT_CAPABILITIES = "A,773,774,775,M01,HM,M05; B,773,774,776,777,M01,HM,M02,M03,M05; C,773,774,776,777,M03; D,773,774,776,777,M02,M03,M05; E,773,774,775,HM; F,776,777,M02,M03; G,771,772,775,M04; H,771,772,773,774,775,M01,HM,M04,M05; I,771,772,773,774,M01h,M01,HM,M04,M05; J,772,773,775,HM; K,771,774,776,777,M01,M03,HM; L,M02; M,771,772,774,M01,HM,M04; N,771,772"
DEFAULT_REQUIREMENTS = "A,8; B,8; C,8; D,8; E,8; F,8; G,8; H,8; I,8; J,8; K,8; L,8; M,8; N,8"

@app.route('/', methods=['GET'])
def index():
    saved_slots = []
    dates_list = []
    
    # 💾 Neonデータベースから最新の保存データを読み込む
    if db:
        try:
            # 1. まず、一番最近保存された「開始日（start_date）」を1つ特定する
            latest_record = ShiftResult.query.order_by(ShiftResult.id.desc()).first()
            if latest_record:
                latest_start = latest_record.start_date
                
                # 2. その開始日に紐づくシフト全件を、日付順・社員名順に取得
                records = ShiftResult.query.filter_by(start_date=latest_start).order_by(ShiftResult.date_str, ShiftResult.employee_name).all()
                
                # 3. 画面で表示しやすいようにデータを整形
                # 重複のない日付リストと社員ごとのシフト辞書を作る
                dates_set = sorted(list(set([r.date_str for r in records])))
                dates_list = dates_set
                
                # 構造: { 'A': ['M01', 'M02', ...], 'B': [...] }
                shift_dict = {}
                for r in records:
                    if r.employee_name not in shift_dict:
                        shift_dict[r.employee_name] = {}
                    shift_dict[r.employee_name][r.date_str] = r.task
                
                # 表（行データ）の形式に変換
                for emp, tasks in shift_dict.items():
                    row = {'employee': emp, 'tasks': [tasks.get(d, '') for d in dates_list]}
                    saved_slots.append(row)
        except Exception as e:
            print(f"⚠️ 画面表示用のデータ読み込みエラー: {e}")

    # 読み込んだ「saved_slots（シフト）」と「dates_list（日付）」をHTMLに引き渡す
    return render_template(
        'index.html', 
        default_caps=DEFAULT_CAPABILITIES, 
        default_reqs=DEFAULT_REQUIREMENTS,
        saved_slots=saved_slots,
        dates_list=dates_list
    )



# @app.route('/', methods=['GET'])
# def index():
#     # データベースが有効なら、過去の最新のシフト開始日を読み込んでみる（おまけ拡張用）
#     saved_shifts = []
#     if db:
#         try:
#             # データベースから最新のレコードを10件取得してみるなど、将来的な表示ロジックをここに組めます
#             pass
#         except:
#             pass
#     return render_template('index.html', default_caps=DEFAULT_CAPABILITIES, default_reqs=DEFAULT_REQUIREMENTS)

@app.route('/generate', methods=['POST'])
def generate():
    try:
        start_date_str = request.form.get('start_date')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        num_days = int(request.form.get('num_days'))
        
        holidays_raw = request.form.get('holidays', '')
        holidays = [h.strip() for h in holidays_raw.split(',') if h.strip()]
        
        hope_holidays_raw = request.form.get('hope_holidays', '').split(';')
        hope_holidays = []
        for item in hope_holidays_raw:
            if ',' in item:
                employee, day = item.split(',')
                hope_holidays.append((employee.strip(), int(day.strip())))

        employee_capabilities = {}
        employees_raw = request.form.get('employees', '').split(';')
        for item in employees_raw:
            if ',' in item:
                parts = item.split(',')
                employee = parts[0].strip()
                skills = [s.strip() for s in parts[1:]]
                employee_capabilities[employee] = skills

        required_holidays = {}
        holidays_required_raw = request.form.get('holiday_requirements', '').split(';')
        for item in holidays_required_raw:
            if ',' in item:
                employee, holiday_count = item.split(',')
                required_holidays[employee.strip()] = int(holiday_count.strip())

        # 1. シフト生成（既存のロジック）
        shift_table = generate_shift_table(
            employee_capabilities, start_date, num_days, holidays, required_holidays, hope_holidays
        )

        # 💾 2. 【新機能】生成したシフトをNeonデータベースに永久保存する
        if db:
            try:
                # 毎回上書きにしたい場合は、今回の開始日の古いデータを一旦削除する
                db.session.query(ShiftResult).filter_by(start_date=start_date_str).delete()
                
                # 社員ごと・日付ごとにバラしてレコードとしてINSERT
                for employee, shifts in shift_table.items():
                    for i, task in enumerate(shifts):
                        current_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
                        record = ShiftResult(
                            start_date=start_date_str,
                            employee_name=employee,
                            date_str=current_date,
                            task=task
                        )
                        db.session.add(record)
                db.session.commit()
                print("💾 Neonデータベースへのシフト保存が正常に完了しました！")
            except Exception as db_error:
                db.session.rollback()
                print(f"⚠️ データベース保存中にエラーが発生（処理は続行します）: {db_error}")

        # 3. Pandasのデータフレームを作成してExcel化（既存のロジック）
        df = pd.DataFrame(shift_table)
        df.index = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(len(list(shift_table.values())[0]))]
        df_transposed = df.transpose()

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_transposed.to_excel(writer, sheet_name='ShiftTable')
        output.seek(0)

        filename = f"shift_{start_date_str}.xlsx"
        return send_file(output, as_attachment=True, download_name=filename, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        return f"エラーが発生しました: {str(e)}", 400

if __name__ == '__main__':
    app.run(debug=True)