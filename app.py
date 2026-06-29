import os
import random
import io
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, send_file # pyright: ignore[reportMissingImports]
import pandas as pd
import mimetypes
from flask_sqlalchemy import SQLAlchemy # pyright: ignore[reportMissingImports]

app = Flask(__name__)
# 📊 最新のペナルティスコアを一時保存する変数
latest_penalty_score = None
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

# ==========================================
# 🧠 🚀 アルゴリズム部分（コアロジック）
# ==========================================

def calculate_total_penalty(special_required_workers, shift_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict, prev_day_shifts):
    """完成したシフト表の不満度（ペナルティ）を計算する関数（低いほど優秀）"""
    total_penalty = 0
    
    # 1. 日ごとのチェック（人数不足）
    for i, date in enumerate(date_list):
        date_str = date.strftime('%Y-%m-%d')
        
        # 必要人数の割り出し（特定日、祝日、土日、平日の順に判定）
        if date_str in special_required_workers:
            required_workers = special_required_workers[date_str]
        elif date_str in holidays:
            required_workers = 5
        elif date.weekday() in [5, 6]:
            required_workers = 6
        else:
            required_workers = 11
            
        working_count = sum(1 for emp in shift_table if shift_table[emp][i] not in ['', 'RH', 'NG'])
        if working_count < required_workers:
            total_penalty += (required_workers - working_count) * 1000

    # 2. 社員ごとのチェック（連勤、希望休違反、総公休数）
    for employee, shifts in shift_table.items():
        consecutive_work = 0
        actual_holidays = 0
        
        # タイムラインの初日のために前月最終日の情報を引き継ぐ
        prev_task = prev_day_shifts.get(employee, '')
        if prev_task not in ['', 'RH', 'NG']:
            consecutive_work = 1  # 前日出勤なら1連勤からスタート（簡易判定）
        
        for i, task in enumerate(shifts):
            date_str = date_list[i].strftime('%Y-%m-%d')
            
            # 希望休なのに出勤させてしまった
            if employee in hope_holidays_dict and date_str in hope_holidays_dict[employee]:
                if task == 'NG' or (task not in ['', 'RH']):
                    total_penalty += 500
            
            # 夜勤（M05）の翌日なのに出勤している（初日は前日データを見る）
            if i == 0:
                if prev_task == 'M05' and task != '':
                    total_penalty += 80
            else:
                if shifts[i-1] == 'M05' and task != '':
                    total_penalty += 80

            # 連勤カウント
            if task not in ['', 'RH']:
                consecutive_work += 1
                if consecutive_work >= 6:
                    total_penalty += 100
            else:
                consecutive_work = 0
                actual_holidays += 1
                
        # 総公休数の不足
        target_holidays = required_holidays.get(employee, 0)
        if actual_holidays < target_holidays:
            total_penalty += (target_holidays - actual_holidays) * 50

    return total_penalty


def generate_single_candidate(special_required_workers, employee_capabilities, date_list, holidays, hope_holidays_dict, prev_day_shifts):
    """ベースとなる初期シフトを1パターン作成する関数"""
    shift_table = {employee: [] for employee in employee_capabilities}
    consecutive_work_days = {employee: 0 for employee in employee_capabilities}
    
    # 前月データの連勤を引き継ぎ
    for employee, last_task in prev_day_shifts.items():
        if employee in consecutive_work_days and last_task not in ['', 'RH', 'NG']:
            consecutive_work_days[employee] = 1

    for i, date in enumerate(date_list):
        date_str = date.strftime('%Y-%m-%d')
        
        if date_str in special_required_workers:
            required_workers = special_required_workers[date_str]
            possible_tasks = ['771', '772', '773', '774', '775', '776', '777', 'M01', 'M02', 'M04', 'M05', 'HM']
        elif date_str in holidays:
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
            # 夜勤（M05）の翌日判定
            is_after_night_shift = False
            if i == 0:
                if prev_day_shifts.get(employee, '') == 'M05':
                    is_after_night_shift = True
            else:
                if shift_table[employee][i-1] == 'M05':
                    is_after_night_shift = True

            if is_after_night_shift:
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
                if date_str in hope_holidays_dict.get(employee, []) and shift_table[employee][-1] == 'RH':
                    shift_table[employee][-1] = 'NG'

    return shift_table


# def refine_by_local_search(special_required_workers, shift_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict, prev_day_shifts, steps=1000):
#     """【局所探索法】ランダムに選んだ2人のタスクを入れ替え、ペナルティが下がれば確定する"""
#     current_table = {emp: list(shifts) for emp, shifts in shift_table.items()}
#     current_penalty = calculate_total_penalty(
#         special_required_workers, current_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict, prev_day_shifts
#     )
    
#     employees = list(employee_capabilities.keys())
#     num_days = len(date_list)
    
#     for _ in range(steps):
#         if current_penalty == 0:
#             break
            
#         target_day = random.randint(0, num_days - 1)
#         emp1, emp2 = random.sample(employees, 2)
        
#         if current_table[emp1][target_day] == current_table[emp2][target_day]:
#             continue
            
#         # スワップ（仮入れ替え）
#         current_table[emp1][target_day], current_table[emp2][target_day] = current_table[emp2][target_day], current_table[emp1][target_day]
        
#         new_penalty = calculate_total_penalty(
#             special_required_workers, current_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict, prev_day_shifts
#         )
        
#         if new_penalty < current_penalty:
#             current_penalty = new_penalty
#         else:
#             # 巻き戻し
#             current_table[emp1][target_day], current_table[emp2][target_day] = current_table[emp2][target_day], current_table[emp1][target_day]
            
#     return current_table, current_penalty
def refine_by_local_search(special_required_workers, shift_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict, prev_day_shifts, steps=1000):
    """【局所探索法】ランダムに選んだ2人のタスクを入れ替え、ペナルティが下がれば確定する"""
    current_table = {emp: list(shifts) for emp, shifts in shift_table.items()}
    current_penalty = calculate_total_penalty(
        special_required_workers, current_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict, prev_day_shifts
    )
    
    employees = list(employee_capabilities.keys())
    num_days = len(date_list)
    
    for _ in range(steps):
        if current_penalty == 0:
            break
            
        target_day = random.randint(0, num_days - 1)
        emp1, emp2 = random.sample(employees, 2)
        
        # 同じタスクならスキップ
        if current_table[emp1][target_day] == current_table[emp2][target_day]:
            continue
            
        # 🚨【ここを追加】入れ替え先のタスクが、お互いのスキルで対応可能かチェック（休みやRH, NGは除外）
        task1 = current_table[emp1][target_day]
        task2 = current_table[emp2][target_day]
        
        if task2 not in ['', 'RH', 'NG'] and task2 not in employee_capabilities[emp1]:
            continue
        if task1 not in ['', 'RH', 'NG'] and task1 not in employee_capabilities[emp2]:
            continue
            
        # スワップ（仮入れ替え）
        current_table[emp1][target_day], current_table[emp2][target_day] = current_table[emp2][target_day], current_table[emp1][target_day]
        
        new_penalty = calculate_total_penalty(
            special_required_workers, current_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict, prev_day_shifts
        )
        
        if new_penalty < current_penalty:
            current_penalty = new_penalty
        else:
            # 巻き戻し
            current_table[emp1][target_day], current_table[emp2][target_day] = current_table[emp2][target_day], current_table[emp1][target_day]
            
    return current_table, current_penalty


def generate_shift_table(special_required_workers, employee_capabilities, start_date, num_days, holidays, required_holidays, hope_holidays, prev_day_shifts, num_candidates=50):
    """ベース候補（50回ガチャ）から局所探索法（1000回揉みほぐし）で限界まで最適化するメイン関数"""
    date_list = [start_date + timedelta(days=i) for i in range(num_days)]

    hope_holidays_dict = {}
    for employee, day in hope_holidays:
        if employee not in hope_holidays_dict:
            hope_holidays_dict[employee] = []
        hope_holidays_dict[employee].append((start_date + timedelta(days=day - 1)).strftime('%Y-%m-%d'))

    best_shift_table = None
    best_penalty = float('inf')

    # 1. 第一段階：50回ガチャを回して、一番マシなベースを1つ選ぶ
    for _ in range(num_candidates):
        candidate_table = generate_single_candidate(
            special_required_workers, employee_capabilities, date_list, holidays, hope_holidays_dict, prev_day_shifts
        )
        
        penalty = calculate_total_penalty(
            special_required_workers, candidate_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict, prev_day_shifts
        )
        
        if penalty < best_penalty:
            best_penalty = penalty
            best_shift_table = candidate_table
            
        if best_penalty == 0:
            break

    print(f"📊 局所探索（入れ替え）前のベストスコア: {best_penalty}点")
    
    # 2. 第二段階：選ばれたベストシフトを、さらに1000回揉みほぐして最適化
    if best_penalty > 0:
        best_shift_table, best_penalty = refine_by_local_search(
            special_required_workers, best_shift_table, employee_capabilities, date_list, holidays, required_holidays, hope_holidays_dict, prev_day_shifts, steps=1000
        )
        print(f"✨ 局所探索（入れ替え）後の最終スコア: {best_penalty}点")
        
    # 最新のスコアをグローバル変数に保持する
    global latest_penalty_score
    latest_penalty_score = best_penalty
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
        dates_list=dates_list,
        penalty_score=latest_penalty_score
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

        # 前月最終日の取得
        last_day_obj = start_date - timedelta(days=1)
        possible_date_formats = [
            last_day_obj.strftime('%Y-%m-%d'),
            f"{last_day_obj.month}/{last_day_obj.day}",
            f"{last_day_obj.year}/{last_day_obj.month}/{last_day_obj.day}"
        ]

        prev_records = ShiftResult.query.filter(ShiftResult.date_str.in_(possible_date_formats)).all()

        prev_day_shifts = {}
        for r in prev_records:
            prev_day_shifts[r.employee_name] = r.task

        print("\n" + "="*50)
        print(f"📡 【システムログ】前月最終日({possible_date_formats[0]})の判定用データを確認中...")
        print(f"🔎 読み込まれた前日データ: {prev_day_shifts}")
        print("="*50 + "\n")
        
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

        # シフト生成（新ロジックへすべてのバトンを正しく渡す）
        shift_table = generate_shift_table(
            special_required_workers, employee_capabilities, start_date, num_days, holidays, required_holidays, hope_holidays, prev_day_shifts, num_candidates=50
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