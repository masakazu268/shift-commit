# import os
# import random
# import io
# from datetime import datetime, timedelta
# from flask import Flask, render_template, request, redirect, url_for, send_file # pyright: ignore[reportMissingImports]
# import pandas as pd
# import mimetypes
# from flask_sqlalchemy import SQLAlchemy # pyright: ignore[reportMissingImports]

# app = Flask(__name__)

# mimetypes.add_type('application/vnd.ms-excel.sheet.macroEnabled.12', '.xlsm')

# # ==========================================
# # 🗄️ データベース（Neon / SQLAlchemy）設定
# # ==========================================
# database_url = os.getenv("DATABASE_URL")

# if database_url and database_url.startswith("postgres://"):
#     database_url = database_url.replace("postgres://", "postgresql://", 1)

# # 環境変数がなければ、ローカルテスト用にSQLiteを使用する（エラー防止）
# if not database_url:
#     database_url = 'sqlite:///local_fallback.db'

# app.config['SQLALCHEMY_DATABASE_URI'] = database_url
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)
    
# # 📝 【新設】社員マスタテーブル
# class Employee(db.Model):
#     __tablename__ = 'employees'
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(50), unique=True, nullable=False) # 社員名
#     skills = db.Column(db.Text, nullable=True)                  # スキル（カンマ区切り文字列）
#     required_holidays = db.Column(db.Integer, default=8)       # 必要休日数

# # 📝 シフト結果を格納するデータベースモデル
# class ShiftResult(db.Model):
#     __tablename__ = 'shift_results'
#     id = db.Column(db.Integer, primary_key=True)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)
#     start_date = db.Column(db.String(10), nullable=False)
#     employee_name = db.Column(db.String(50), nullable=False)
#     date_str = db.Column(db.String(10), nullable=False)
#     task = db.Column(db.String(10))

# # アプリ起動時にテーブルを自動作成し、初期データがなければ投入する
# with app.app_context():
#     db.create_all()
    
#     # 初回起動時のみデフォルトの社員データを登録する
#     if Employee.query.count() == 0:
#         default_data = [
#             ("A", "773,774,775,M01,HM,M05", 8),
#             ("B", "773,774,776,777,M01,HM,M02,M03,M05", 8),
#             ("C", "773,774,776,777,M03", 8),
#             ("D", "773,774,776,777,M02,M03,M05", 8),
#             ("E", "773,774,775,HM", 8),
#             ("F", "776,777,M02,M03", 8),
#             ("G", "771,772,775,M04", 8),
#             ("H", "771,772,773,774,775,M01,HM,M04,M05", 8),
#             ("I", "771,772,773,774,M01h,M01,HM,M04,M05", 8),
#             ("J", "772,773,775,HM", 8),
#             ("K", "771,774,776,777,M01,M03,HM", 8),
#             ("L", "M02", 8),
#             ("M", "771,772,774,M01,HM,M04", 8),
#             ("N", "771,772", 8)
#         ]
#         for name, skills, hol in default_data:
#             emp = Employee(name=name, skills=skills, required_holidays=hol)
#             db.session.add(emp)
#         db.session.commit()

# # --- [ロジック部分] 既存のコードをそのまま保持 ---
# def is_weekend_or_holiday(date, holidays):
#     return date.weekday() >= 5 or date.strftime('%Y-%m-%d') in holidays

# def check_employee_holidays(employee_holidays, required_holidays):
#     for employee, holidays in employee_holidays.items():
#         if holidays < required_holidays.get(employee, 0):
#             return False
#     return True

# def calculate_total_penalty(special_required_workers,shift_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict):
#     total_penalty = 0
#     for i, date in enumerate(date_list):
#         date_str = date.strftime('%Y-%m-%d')
#         if date_str in holidays:
#             required_workers = 5
#         elif date.weekday() in [5, 6]:
#             required_workers = 6
#         else:
#             required_workers = 11
            
#         working_count = 0
#         for employee in shift_table:
#             task = shift_table[employee][i]
#             if task not in ['', 'RH', 'NG']:
#                 working_count += 1
                
#         if working_count < required_workers:
#             shortage = required_workers - working_count
#             total_penalty += shortage * 1000

#     for employee, shifts in shift_table.items():
#         consecutive_work = 0
#         actual_holidays = 0
        
#         for i, task in enumerate(shifts):
#             date_str = date_list[i].strftime('%Y-%m-%d')
            
#             if employee in hope_holidays_dict and date_str in hope_holidays_dict[employee]:
#                 if task == 'NG' or (task not in ['', 'RH']):
#                     total_penalty += 500
            
#             if i > 0 and shifts[i-1] == 'M05':
#             # 🚨 夜勤の翌日に「M01」が入っていたら、かなり厳しいペナルティを課す
#                 if task == 'M01':
#                     total_penalty += 200  # 絶対に回避したいので点数を高めに設定
#                     # 💡 逆に「M01」以外（M02, M04, 771 など）や「空白（休み）」ならペナルティ0点（OK！）
            
#             # if i > 0 and shifts[i-1] == 'M05':
#             #     if task != '':
#             #         total_penalty += 10

#             if task not in ['', 'RH']:
#                 consecutive_work += 1
#                 if consecutive_work >= 6:
#                     total_penalty += 100
#             else:
#                 consecutive_work = 0
#                 actual_holidays += 1
                
#         target_holidays = required_holidays.get(employee, 0)
#         if actual_holidays < target_holidays:
#             shortage_days = target_holidays - actual_holidays
#             total_penalty += shortage_days * 50

#     return total_penalty

# def generate_single_candidate(special_required_workers,employee_capabilities, date_list, holidays, hope_holidays_dict):
#     shift_table = {employee: [] for employee in employee_capabilities}
#     consecutive_work_days = {employee: 0 for employee in employee_capabilities}
    
#     for i, date in enumerate(date_list):
#         date_str = date.strftime('%Y-%m-%d')

#         # 1. 任意の日付指定があればそれを最優先
#     if date_str in special_required_workers:
#         required_workers = special_required_workers[date_str]
#     # 2. なければ通常の曜日・祝日ルール
#     elif date_str in holidays:
#         required_workers = 5
#     elif date.weekday() in [5, 6]:
#         required_workers = 6
#     else:
#         required_workers = 11
        
        
        
        
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
#             if i > 0 and shift_table[employee][i-1] == 'M05':
#                 shift_table[employee].append('')
#                 consecutive_work_days[employee] = 0
#                 continue

#             if employee in hope_holidays_dict and date_str in hope_holidays_dict[employee]:
#                 shift_table[employee].append('RH')
#                 consecutive_work_days[employee] = 0
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

#         if len(day_tasks) < required_workers:
#             for employee in shift_table.keys():
#                 if date_str in hope_holidays_dict.get(employee, []):
#                     if shift_table[employee][-1] == 'RH':
#                         shift_table[employee][-1] = 'NG'

#     return shift_table

# def generate_shift_table(special_required_workers, employee_capabilities, start_date, num_days, holidays, required_holidays, hope_holidays, num_candidates=50):
#     date_list = [start_date + timedelta(days=i) for i in range(num_days)]

#     hope_holidays_dict = {}
#     for employee, day in hope_holidays:
#         if employee not in hope_holidays_dict:
#             hope_holidays_dict[employee] = []
#         hope_holidays_dict[employee].append((start_date + timedelta(days=day - 1)).strftime('%Y-%m-%d'))

#     best_shift_table = None
#     best_penalty = float('inf')

#     for _ in range(num_candidates):
#         candidate_table = generate_single_candidate(employee_capabilities, date_list, holidays, hope_holidays_dict)
#         penalty = calculate_total_penalty(
#             candidate_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict
#         )
#         if penalty < best_penalty:
#             best_penalty = penalty
#             best_shift_table = candidate_table
            
#         if best_penalty == 0:
#             break

#     print(f"🎉 採用されたシフトのペナルティスコア: {best_penalty}点")
#     return best_shift_table


# # ==========================================
# # ⚙️ ルーティング（画面表示とCRUD処理）
# # ==========================================

# @app.route('/', methods=['GET'])
# def index():
#     saved_slots = []
#     dates_list = []
    
#     # 1. データベースから現在の社員マスタの一覧を取得
#     employees_list = Employee.query.order_by(Employee.name).all()
    
#     # 生成フォームのテキストエリア用に、DBのデータを元に「A,スキル...; B,スキル...」の文字列を自動作成する
#     caps_strings = []
#     reqs_strings = []
#     for emp in employees_list:
#         caps_strings.append(f"{emp.name},{emp.skills}")
#         reqs_strings.append(f"{emp.name},{emp.required_holidays}")
    
#     generated_caps = " ; ".join(caps_strings)
#     generated_reqs = " ; ".join(reqs_strings)

#     # 2. 最新の保存済みシフト結果を読み込む
#     try:
#         latest_record = ShiftResult.query.order_by(ShiftResult.id.desc()).first()
#         if latest_record:
#             latest_start = latest_record.start_date
#             records = ShiftResult.query.filter_by(start_date=latest_start).order_by(ShiftResult.date_str, ShiftResult.employee_name).all()
            
#             dates_set = sorted(list(set([r.date_str for r in records])))
#             dates_list = dates_set
            
#             shift_dict = {}
#             for r in records:
#                 if r.employee_name not in shift_dict:
#                     shift_dict[r.employee_name] = {}
#                 shift_dict[r.employee_name][r.date_str] = r.task
            
#             for emp_name in sorted(shift_dict.keys()):
#                 row = {'employee': emp_name, 'tasks': [shift_dict[emp_name].get(d, '') for d in dates_list]}
#                 saved_slots.append(row)
#     except Exception as e:
#         print(f"⚠️ シフトデータ読み込みエラー: {e}")

#     return render_template(
#         'index.html', 
#         employees_list=employees_list,   # 社員一覧マスタ（CRUD用）
#         default_caps=generated_caps,     # 生成フォームへ渡すスキル文字列
#         default_reqs=generated_reqs,     # 生成フォームへ渡す休日数文字列
#         saved_slots=saved_slots,
#         dates_list=dates_list
#     )

# # ➕ 【Create】社員マスタへの追加
# @app.route('/employee/add', methods=['POST'])
# def add_employee():
#     name = request.form.get('name').strip()
#     skills = request.form.get('skills').strip()
#     required_holidays = int(request.form.get('required_holidays', 8))
    
#     if name:
#         # 重複チェック。なければ追加
#         exists = Employee.query.filter_by(name=name).first()
#         if not exists:
#             new_emp = Employee(name=name, skills=skills, required_holidays=required_holidays)
#             db.session.add(new_emp)
#             db.session.commit()
#     return redirect(url_for('index'))

# # 🔄 【Update】社員マスタの更新
# @app.route('/employee/update/<int:id>', methods=['POST'])
# def update_employee(id):
#     emp = Employee.query.get_or_404(id)
#     emp.name = request.form.get('name').strip()
#     emp.skills = request.form.get('skills').strip()
#     emp.required_holidays = int(request.form.get('required_holidays', 8))
#     db.session.commit()
#     return redirect(url_for('index'))

# # 🗑️ 【Delete】社員マスタからの削除
# @app.route('/employee/delete/<int:id>', methods=['POST'])
# def delete_employee(id):
#     emp = Employee.query.get_or_404(id)
#     db.session.delete(emp)
#     db.session.commit()
#     return redirect(url_for('index'))


# @app.route('/generate', methods=['POST'])
# def generate():

#     try:
#         # --- @app.route('/generate') の try の中に追加 ---
#         special_required_workers = {}
#         special_workers_raw = request.form.get('special_workers', '').split(';')
#         for item in special_workers_raw:
#             if ',' in item:
#                 date_part, count_part = item.split(',')
#                 special_required_workers[date_part.strip()] = int(count_part.strip())   
        
        
        
        
        
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

#         employee_capabilities = {}
#         # ⚠️ 注意: 画面から送られてくるセミコロン区切りのデータを正しく解析するように修正
#         employees_raw = request.form.get('employees', '').split(';')
#         for item in employees_raw:
#             if ',' in item:
#                 parts = item.split(',')
#                 employee = parts[0].strip()
#                 skills = [s.strip() for s in parts[1:] if s.strip()]
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

#         # 💾 シフトをNeonデータベースに永久保存
#         try:
#             db.session.query(ShiftResult).filter_by(start_date=start_date_str).delete()
#             for employee, shifts in shift_table.items():
#                 for i, task in enumerate(shifts):
#                     current_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
#                     record = ShiftResult(
#                         start_date=start_date_str,
#                         employee_name=employee,
#                         date_str=current_date,
#                         task=task
#                     )
#                     db.session.add(record)
#             db.session.commit()
#         except Exception as db_error:
#             db.session.rollback()
#             print(f"⚠️ データベース保存中にエラー: {db_error}")

#         # Excelの出力処理
#         df = pd.DataFrame(shift_table)
#         df.index = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(len(list(shift_table.values())[0]))]
#         df_transposed = df.transpose()

#         output = io.BytesIO()
#         with pd.ExcelWriter(output, engine='openpyxl') as writer:
#             df_transposed.to_excel(writer, sheet_name='ShiftTable')
#         output.seek(0)

#         filename = f"shift_{start_date_str}.xlsx"
#         return send_file(output, as_attachment=True, download_name=filename, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

#     except Exception as e:
#         return f"エラーが発生しました: {str(e)}", 400

# if __name__ == '__main__':
#     app.run(debug=True)

# import os
# import random
# import io
# from datetime import datetime, timedelta
# from flask import Flask, render_template, request, redirect, url_for, send_file # pyright: ignore[reportMissingImports]
# import pandas as pd
# import mimetypes
# from flask_sqlalchemy import SQLAlchemy # pyright: ignore[reportMissingImports]

# app = Flask(__name__)

# mimetypes.add_type('application/vnd.ms-excel.sheet.macroEnabled.12', '.xlsm')

# # ==========================================
# # 🗄️ データベース（Neon / SQLAlchemy）設定
# # ==========================================
# database_url = os.getenv("DATABASE_URL")

# if database_url and database_url.startswith("postgres://"):
#     database_url = database_url.replace("postgres://", "postgresql://", 1)

# # 環境変数がなければ、ローカルテスト用にSQLiteを使用する（エラー防止）
# if not database_url:
#     database_url = 'sqlite:///local_fallback.db'

# app.config['SQLALCHEMY_DATABASE_URI'] = database_url
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)
    
# # 📝 社員マスタテーブル
# class Employee(db.Model):
#     __tablename__ = 'employees'
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(50), unique=True, nullable=False) # 社員名
#     skills = db.Column(db.Text, nullable=True)                  # スキル（カンマ区切り文字列）
#     required_holidays = db.Column(db.Integer, default=8)       # 必要休日数

# # 📝 シフト結果を格納するデータベースモデル
# class ShiftResult(db.Model):
#     __tablename__ = 'shift_results'
#     id = db.Column(db.Integer, primary_key=True)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)
#     start_date = db.Column(db.String(10), nullable=False)
#     employee_name = db.Column(db.String(50), nullable=False)
#     date_str = db.Column(db.String(10), nullable=False)
#     task = db.Column(db.String(10))

# # アプリ起動時にテーブルを自動作成し、初期データがなければ投入する
# with app.app_context():
#     db.create_all()
    
#     # 初回起動時のみデフォルトの社員データを登録する
#     if Employee.query.count() == 0:
#         default_data = [
#             ("A", "773,774,775,M01,HM,M05", 8),
#             ("B", "773,774,776,777,M01,HM,M02,M03,M05", 8),
#             ("C", "773,774,776,777,M03", 8),
#             ("D", "773,774,776,777,M02,M03,M05", 8),
#             ("E", "773,774,775,HM", 8),
#             ("F", "776,777,M02,M03", 8),
#             ("G", "771,772,775,M04", 8),
#             ("H", "771,772,773,774,775,M01,HM,M04,M05", 8),
#             ("I", "771,772,773,774,M01h,M01,HM,M04,M05", 8),
#             ("J", "772,773,775,HM", 8),
#             ("K", "771,774,776,777,M01,M03,HM", 8),
#             ("L", "M02", 8),
#             ("M", "771,772,774,M01,HM,M04", 8),
#             ("N", "771,772", 8)
#         ]
#         for name, skills, hol in default_data:
#             emp = Employee(name=name, skills=skills, required_holidays=hol)
#             db.session.add(emp)
#         db.session.commit()

# # --- [ロジック部分] 既存のコードをそのまま保持 ---
# def is_weekend_or_holiday(date, holidays):
#     return date.weekday() >= 5 or date.strftime('%Y-%m-%d') in holidays

# def check_employee_holidays(employee_holidays, required_holidays):
#     for employee, holidays in employee_holidays.items():
#         if holidays < required_holidays.get(employee, 0):
#             return False
#     return True

# # 🧮 ペナルティスコア計算（特定日上書き対応版）
# def calculate_total_penalty(special_required_workers, shift_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict):
#     total_penalty = 0
#     for i, date in enumerate(date_list):
#         date_str = date.strftime('%Y-%m-%d')
        
#         # 🌟 1. 特定日の指定があれば最優先、なければ曜日ルール
#         if date_str in special_required_workers:
#             required_workers = special_required_workers[date_str]
#         elif date_str in holidays:
#             required_workers = 5
#         elif date.weekday() in [5, 6]:
#             required_workers = 6
#         else:
#             required_workers = 11
            
#         working_count = 0
#         for employee in shift_table:
#             task = shift_table[employee][i]
#             if task not in ['', 'RH', 'NG']:
#                 working_count += 1
                
#         if working_count < required_workers:
#             shortage = required_workers - working_count
#             total_penalty += shortage * 1000

#     for employee, shifts in shift_table.items():
#         consecutive_work = 0
#         actual_holidays = 0
        
#         for i, task in enumerate(shifts):
#             date_str = date_list[i].strftime('%Y-%m-%d')
            
#             if employee in hope_holidays_dict and date_str in hope_holidays_dict[employee]:
#                 if task == 'NG' or (task not in ['', 'RH']):
#                     total_penalty += 500
            
#             if i > 0 and shifts[i-1] == 'M05':
#                 if task != '':
#                     total_penalty += 10

#             if task not in ['', 'RH']:
#                 consecutive_work += 1
#                 if consecutive_work >= 6:
#                     total_penalty += 100
#             else:
#                 consecutive_work = 0
#                 actual_holidays += 1
                
#         target_holidays = required_holidays.get(employee, 0)
#         if actual_holidays < target_holidays:
#             shortage_days = target_holidays - actual_holidays
#             total_penalty += shortage_days * 50

#     return total_penalty

# # 🧬 シフト候補生成（特定日上書き・人数別タスク制限対応版）
# def generate_single_candidate(special_required_workers, employee_capabilities, date_list, holidays, hope_holidays_dict):
#     shift_table = {employee: [] for employee in employee_capabilities}
#     consecutive_work_days = {employee: 0 for employee in employee_capabilities}
    
#     for i, date in enumerate(date_list):
#         date_str = date.strftime('%Y-%m-%d')

#         # 🌟 1. 任意の日付指定（上書き）があればそれを最優先
#         if date_str in special_required_workers:
#             required_workers = special_required_workers[date_str]
#             # 指定された人数に応じて、選べるタスクを最適化
#             if required_workers <= 5:
#                 possible_tasks = ['M01', 'M02', 'M03', 'M04', 'M05']
#             elif required_workers == 6:
#                 possible_tasks = ['M01', 'HM', 'M02', 'M03', 'M04', 'M05']
#             else:
#                 possible_tasks = ['771', '772', '773', '774', '775', '776', '777', 'M01', 'M02', 'M04', 'M05']
#         # 2. なければ通常の曜日・祝日ルール
#         elif date_str in holidays:
#             required_workers = 5
#             possible_tasks = ['M01', 'M02', 'M03', 'M04', 'M05']
#         elif date.weekday() in [5, 6]:
#             required_workers = 6
#             possible_tasks = ['M01', 'HM', 'M02', 'M03', 'M04', 'M05']
#         else:
#             required_workers = 11
#             possible_tasks = ['771', '772', '773', '774', '775', '776', '777', 'M01', 'M02', 'M04', 'M05']

#         day_tasks = set()
#         employees = list(employee_capabilities.keys())
#         random.shuffle(employees)

#         for employee in employees:
#             if i > 0 and shift_table[employee][i-1] == 'M05':
#                 shift_table[employee].append('')
#                 consecutive_work_days[employee] = 0
#                 continue

#             if employee in hope_holidays_dict and date_str in hope_holidays_dict[employee]:
#                 shift_table[employee].append('RH')
#                 consecutive_work_days[employee] = 0
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

#         if len(day_tasks) < required_workers:
#             for employee in shift_table.keys():
#                 if date_str in hope_holidays_dict.get(employee, []):
#                     if shift_table[employee][-1] == 'RH':
#                         shift_table[employee][-1] = 'NG'

#     return shift_table

# def generate_shift_table(special_required_workers, employee_capabilities, start_date, num_days, holidays, required_holidays, hope_holidays, num_candidates=50):
#     date_list = [start_date + timedelta(days=i) for i in range(num_days)]

#     hope_holidays_dict = {}
#     for employee, day in hope_holidays:
#         if employee not in hope_holidays_dict:
#             hope_holidays_dict[employee] = []
#         hope_holidays_dict[employee].append((start_date + timedelta(days=day - 1)).strftime('%Y-%m-%d'))

#     best_shift_table = None
#     best_penalty = float('inf')

#     for _ in range(num_candidates):
#         candidate_table = generate_single_candidate(special_required_workers, employee_capabilities, date_list, holidays, hope_holidays_dict)
#         penalty = calculate_total_penalty(
#             special_required_workers, candidate_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict
#         )
#         if penalty < best_penalty:
#             best_penalty = penalty
#             best_shift_table = candidate_table
            
#         if best_penalty == 0:
#             break

#     print(f"🎉 採用されたシフトのペナルティスコア: {best_penalty}点")
#     return best_shift_table


# # ==========================================
# # ⚙️ ルーティング（画面表示とCRUD処理）
# # ==========================================

# @app.route('/', methods=['GET'])
# def index():
#     saved_slots = []
#     dates_list = []
    
#     # 1. データベースから現在の社員マスタの一覧を取得
#     employees_list = Employee.query.order_by(Employee.name).all()
    
#     # 生成フォームのテキストエリア用に、DBのデータを元に「A,スキル...; B,スキル...」の文字列を自動作成する
#     caps_strings = []
#     reqs_strings = []
#     for emp in employees_list:
#         caps_strings.append(f"{emp.name},{emp.skills}")
#         reqs_strings.append(f"{emp.name},{emp.required_holidays}")
    
#     generated_caps = "; ".join(caps_strings)
#     generated_reqs = "; ".join(reqs_strings)

#     # 2. 最新の保存済みシフト結果を読み込む
#     try:
#         latest_record = ShiftResult.query.order_by(ShiftResult.id.desc()).first()
#         if latest_record:
#             latest_start = latest_record.start_date
#             records = ShiftResult.query.filter_by(start_date=latest_start).order_by(ShiftResult.date_str, ShiftResult.employee_name).all()
            
#             dates_set = sorted(list(set([r.date_str for r in records])))
#             dates_list = dates_set
            
#             shift_dict = {}
#             for r in records:
#                 if r.employee_name not in shift_dict:
#                     shift_dict[r.employee_name] = {}
#                 shift_dict[r.employee_name][r.date_str] = r.task
            
#             for emp_name in sorted(shift_dict.keys()):
#                 row = {'employee': emp_name, 'tasks': [shift_dict[emp_name].get(d, '') for d in dates_list]}
#                 saved_slots.append(row)
#     except Exception as e:
#         print(f"⚠️ シフトデータ読み込みエラー: {e}")

#     return render_template(
#         'index.html', 
#         employees_list=employees_list,   # 社員一覧マスタ（CRUD用）
#         default_caps=generated_caps,     # 生成フォームへ渡すスキル文字列
#         default_reqs=generated_reqs,     # 生成フォームへ渡す休日数文字列
#         saved_slots=saved_slots,
#         dates_list=dates_list
#     )

# # ➕ 【Create】社員マスタへの追加
# @app.route('/employee/add', methods=['POST'])
# def add_employee():
#     name = request.form.get('name').strip()
#     skills = request.form.get('skills').strip()
#     required_holidays = int(request.form.get('required_holidays', 8))
    
#     if name:
#         exists = Employee.query.filter_by(name=name).first()
#         if not exists:
#             new_emp = Employee(name=name, skills=skills, required_holidays=required_holidays)
#             db.session.add(new_emp)
#             db.session.commit()
#     return redirect(url_for('index'))

# # 🔄 【Update】社員マスタの更新
# @app.route('/employee/update/<int:id>', methods=['POST'])
# def update_employee(id):
#     emp = Employee.query.get_or_404(id)
#     emp.name = request.form.get('name').strip()
#     emp.skills = request.form.get('skills').strip()
#     emp.required_holidays = int(request.form.get('required_holidays', 8))
#     db.session.commit()
#     return redirect(url_for('index'))

# # 🗑️ 【Delete】社員マスタからの削除
# @app.route('/employee/delete/<int:id>', methods=['POST'])
# def delete_employee(id):
#     emp = Employee.query.get_or_404(id)
#     db.session.delete(emp)
#     db.session.commit()
#     return redirect(url_for('index'))


# @app.route('/generate', methods=['POST'])
# def generate():
#     try:
#         # 📅 特定日の上書きデータパース処理
#         special_required_workers = {}
#         special_workers_raw = request.form.get('special_workers', '').split(';')
#         for item in special_workers_raw:
#             if ',' in item:
#                 date_part, count_part = item.split(',')
#                 special_required_workers[date_part.strip()] = int(count_part.strip())   
        
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

#         employee_capabilities = {}
#         employees_raw = request.form.get('employees', '').split(';')
#         for item in employees_raw:
#             if ',' in item:
#                 parts = item.split(',')
#                 employee = parts[0].strip()
#                 skills = [s.strip() for s in parts[1:] if s.strip()]
#                 employee_capabilities[employee] = skills

#         required_holidays = {}
#         holidays_required_raw = request.form.get('holiday_requirements', '').split(';')
#         for item in holidays_required_raw:
#             if ',' in item:
#                 employee, holiday_count = item.split(',')
#                 required_holidays[employee.strip()] = int(holiday_count.strip())

#         # シフト生成（新引数を追加）
#         shift_table = generate_shift_table(
#             special_required_workers, employee_capabilities, start_date, num_days, holidays, required_holidays, hope_holidays
#         )

#         # 💾 シフトをNeonデータベースに永久保存
#         try:
#             db.session.query(ShiftResult).filter_by(start_date=start_date_str).delete()
#             for employee, shifts in shift_table.items():
#                 for i, task in enumerate(shifts):
#                     current_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
#                     record = ShiftResult(
#                         start_date=start_date_str,
#                         employee_name=employee,
#                         date_str=current_date,
#                         task=task
#                     )
#                     db.session.add(record)
#             db.session.commit()
#         except Exception as db_error:
#             db.session.rollback()
#             print(f"⚠️ データベース保存中にエラー: {db_error}")

#         # Excelの出力処理
#         df = pd.DataFrame(shift_table)
#         df.index = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(len(list(shift_table.values())[0]))]
#         df_transposed = df.transpose()

#         output = io.BytesIO()
#         with pd.ExcelWriter(output, engine='openpyxl') as writer:
#             df_transposed.to_excel(writer, sheet_name='ShiftTable')
#         output.seek(0)

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
from flask import Flask, render_template, request, redirect, url_for, send_file # pyright: ignore[reportMissingImports]
import pandas as pd
import mimetypes
from flask_sqlalchemy import SQLAlchemy # pyright: ignore[reportMissingImports]

app = Flask(__name__)

mimetypes.add_type('application/vnd.ms-excel.sheet.macroEnabled.12', '.xlsm')

# ==========================================
# 🗄️ データベース（Neon / SQLAlchemy）設定
# ==========================================
database_url = os.getenv("DATABASE_URL")

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

if not database_url:
    database_url = 'sqlite:///local_fallback.db'

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
    
class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    skills = db.Column(db.Text, nullable=True)                  
    required_holidays = db.Column(db.Integer, default=8)       

class ShiftResult(db.Model):
    __tablename__ = 'shift_results'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    start_date = db.Column(db.String(10), nullable=False)
    employee_name = db.Column(db.String(50), nullable=False)
    date_str = db.Column(db.String(10), nullable=False)
    task = db.Column(db.String(10))

with app.app_context():
    db.create_all()
    if Employee.query.count() == 0:
        default_data = [
            ("A", "773,774,775,M01,HM,M05", 8),
            ("B", "773,774,776,777,M01,HM,M02,M03,M05", 8),
            ("C", "773,774,776,777,M03", 8),
            ("D", "773,774,776,777,M02,M03,M05", 8),
            ("E", "773,774,775,HM", 8),
            ("F", "776,777,M02,M03", 8),
            ("G", "771,772,775,M04", 8),
            ("H", "771,772,773,774,775,M01,HM,M04,M05", 8),
            ("I", "771,772,773,774,M01h,M01,HM,M04,M05", 8),
            ("J", "772,773,775,HM", 8),
            ("K", "771,774,776,777,M01,M03,HM", 8),
            ("L", "M02", 8),
            ("M", "771,772,774,M01,HM,M04", 8),
            ("N", "771,772", 8)
        ]
        for name, skills, hol in default_data:
            emp = Employee(name=name, skills=skills, required_holidays=hol)
            db.session.add(emp)
        db.session.commit()

def is_weekend_or_holiday(date, holidays):
    return date.weekday() >= 5 or date.strftime('%Y-%m-%d') in holidays

def check_employee_holidays(employee_holidays, required_holidays):
    for employee, holidays in employee_holidays.items():
        if holidays < required_holidays.get(employee, 0):
            return False
    return True

# 🧮 ペナルティスコア計算
def calculate_total_penalty(special_required_workers, shift_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict):
    total_penalty = 0
    for i, date in enumerate(date_list):
        date_str = date.strftime('%Y-%m-%d')
        
        if date_str in special_required_workers:
            required_workers = special_required_workers[date_str]
        elif date_str in holidays:
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
            
            # 🌟【ルール緩和】夜勤（M05）の翌日に、きつい早番（M01）が入っていたらNG（高ペナルティ）
            # それ以外の遅番（M02やM04など）や休みならペナルティ0で許容する
            # if i > 0 and shifts[i-1] == 'M05':
            #     if task == 'M01':
            #         total_penalty += 200
            # 夜勤の翌日に、禁止タスク（M01, 771, 772,'773', '774', '775','777'）のいずれかが入っていたらNG
            if i > 0 and shifts[i-1] == 'M05':
                if task in ['M01', 'M02','771', '772', '773', '774', '775','777']:
                    total_penalty += 200

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

# 🧬 シフト候補生成
def generate_single_candidate(special_required_workers, employee_capabilities, date_list, holidays, hope_holidays_dict):
    shift_table = {employee: [] for employee in employee_capabilities}
    consecutive_work_days = {employee: 0 for employee in employee_capabilities}
    
    for i, date in enumerate(date_list):
        date_str = date.strftime('%Y-%m-%d')

        if date_str in special_required_workers:
            required_workers = special_required_workers[date_str]
            if required_workers <= 5:
                possible_tasks = ['M01', 'M02', 'M03', 'M04', 'M05']
            elif required_workers == 6:
                possible_tasks = ['M01', 'HM', 'M02', 'M03', 'M04', 'M05']
            else:
                possible_tasks = ['771', '772', '773', '774', '775', '776', '777', 'M01', 'M02', 'M04', 'M05']
        elif date_str in holidays:
            required_workers = 5
            possible_tasks = ['M01', 'M02', 'M03', 'M04', 'M05']
        elif date.weekday() in [5, 6]:
            required_workers = 6
            possible_tasks = ['M01', 'HM', 'M02', 'M03', 'M04', 'M05']
        else:
            required_workers = 11
            possible_tasks = ['771', '772', '773', '774', '775', '776', '777', 'M01', 'M02', 'M04', 'M05']

        day_tasks = set()
        employees = list(employee_capabilities.keys())
        random.shuffle(employees)

        for employee in employees:
            # 🌟【生成ロジックの適応】前日が夜勤（M05）の場合、当日の候補から「M01」を絶対に除外する
            if i > 0 and shift_table[employee][i-1] == 'M05':
                current_possible_tasks = [t for t in possible_tasks if t != 'M01']
            else:
                current_possible_tasks = possible_tasks

            if employee in hope_holidays_dict and date_str in hope_holidays_dict[employee]:
                shift_table[employee].append('RH')
                consecutive_work_days[employee] = 0
            elif len(day_tasks) < required_workers and consecutive_work_days[employee] < 5:
                possible_employee_tasks = [task for task in employee_capabilities[employee] if task in current_possible_tasks and task not in day_tasks]
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

# 📋 シフトテーブル管理（引数の順番を整理）
def generate_shift_table(special_required_workers, employee_capabilities, start_date, num_days, holidays, required_holidays, hope_holidays, num_candidates=50):
    date_list = [start_date + timedelta(days=i) for i in range(num_days)]

    hope_holidays_dict = {}
    for employee, day in hope_holidays:
        if employee not in hope_holidays_dict:
            hope_holidays_dict[employee] = []
        hope_holidays_dict[employee].append((start_date + timedelta(days=day - 1)).strftime('%Y-%m-%d'))

    best_shift_table = None
    best_penalty = float('inf')

    for _ in range(num_candidates):
        candidate_table = generate_single_candidate(special_required_workers, employee_capabilities, date_list, holidays, hope_holidays_dict)
        penalty = calculate_total_penalty(
            special_required_workers, candidate_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict
        )
        if penalty < best_penalty:
            best_penalty = penalty
            best_shift_table = candidate_table
            
        if best_penalty == 0:
            break

    print(f"🎉 採用されたシフトのペナルティスコア: {best_penalty}点")
    return best_shift_table


# ==========================================
# ⚙️ ルーティング（画面表示とCRUD処理）
# ==========================================

@app.route('/', methods=['GET'])
def index():
    saved_slots = []
    dates_list = []
    
    employees_list = Employee.query.order_by(Employee.name).all()
    
    caps_strings = []
    reqs_strings = []
    for emp in employees_list:
        caps_strings.append(f"{emp.name},{emp.skills}")
        reqs_strings.append(f"{emp.name},{emp.required_holidays}")
    
    generated_caps = "; ".join(caps_strings)
    generated_reqs = "; ".join(reqs_strings)

    try:
        latest_record = ShiftResult.query.order_by(ShiftResult.id.desc()).first()
        if latest_record:
            latest_start = latest_record.start_date
            records = ShiftResult.query.filter_by(start_date=latest_start).order_by(ShiftResult.date_str, ShiftResult.employee_name).all()
            
            dates_set = sorted(list(set([r.date_str for r in records])))
            dates_list = dates_set
            
            shift_dict = {}
            for r in records:
                if r.employee_name not in shift_dict:
                    shift_dict[r.employee_name] = {}
                shift_dict[r.employee_name][r.date_str] = r.task
            
            for emp_name in sorted(shift_dict.keys()):
                row = {'employee': emp_name, 'tasks': [shift_dict[emp_name].get(d, '') for d in dates_list]}
                saved_slots.append(row)
    except Exception as e:
        print(f"⚠️ シフトデータ読み込みエラー: {e}")

    return render_template(
        'index.html', 
        employees_list=employees_list,   
        default_caps=generated_caps,     
        default_reqs=generated_reqs,     
        saved_slots=saved_slots,
        dates_list=dates_list
    )

@app.route('/employee/add', methods=['POST'])
def add_employee():
    name = request.form.get('name').strip()
    skills = request.form.get('skills').strip()
    required_holidays = int(request.form.get('required_holidays', 8))
    
    if name:
        exists = Employee.query.filter_by(name=name).first()
        if not exists:
            new_emp = Employee(name=name, skills=skills, required_holidays=required_holidays)
            db.session.add(new_emp)
            db.session.commit()
    return redirect(url_for('index'))

@app.route('/employee/update/<int:id>', methods=['POST'])
def update_employee(id):
    emp = Employee.query.get_or_404(id)
    emp.name = request.form.get('name').strip()
    emp.skills = request.form.get('skills').strip()
    emp.required_holidays = int(request.form.get('required_holidays', 8))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/employee/delete/<int:id>', methods=['POST'])
def delete_employee(id):
    emp = Employee.query.get_or_404(id)
    db.session.delete(emp)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/generate', methods=['POST'])
def generate():
    try:
        special_required_workers = {}
        special_workers_raw = request.form.get('special_workers', '').split(';')
        for item in special_workers_raw:
            if ',' in item:
                date_part, count_part = item.split(',')
                special_required_workers[date_part.strip()] = int(count_part.strip())   
        
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
                skills = [s.strip() for s in parts[1:] if s.strip()]
                employee_capabilities[employee] = skills

        required_holidays = {}
        holidays_required_raw = request.form.get('holiday_requirements', '').split(';')
        for item in holidays_required_raw:
            if ',' in item:
                employee, holiday_count = item.split(',')
                required_holidays[employee.strip()] = int(holiday_count.strip())

        # 🌟【引数エラー解消】すべての引数の順番と個数を完全に一致させて呼び出し
        shift_table = generate_shift_table(
            special_required_workers, employee_capabilities, start_date, num_days, holidays, required_holidays, hope_holidays, num_candidates=50
        )

        try:
            db.session.query(ShiftResult).filter_by(start_date=start_date_str).delete()
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
        except Exception as db_error:
            db.session.rollback()
            print(f"⚠️ データベース保存中にエラー: {db_error}")

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