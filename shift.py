import os
import random
import io
from datetime import datetime, timedelta
from flask import Flask, render_template, request, send_file
import pandas as pd

app = Flask(__name__)

# --- [ロジック部分] 既存のコードをそのまま活用 ---
def is_weekend_or_holiday(date, holidays):
    return date.weekday() >= 5 or date.strftime('%Y-%m-%d') in holidays

def check_employee_holidays(employee_holidays, required_holidays):
    for employee, holidays in employee_holidays.items():
        if holidays < required_holidays.get(employee, 0):
            return False
    return True

def generate_shift_table(employee_capabilities, start_date, num_days, holidays, required_holidays, hope_holidays, max_iterations=30000):
    shift_table = {employee: [] for employee in employee_capabilities}
    employee_holidays = {employee: 0 for employee in employee_capabilities}
    consecutive_work_days = {employee: 0 for employee in employee_capabilities}
    
    date_list = [start_date + timedelta(days=i) for i in range(num_days)]

    hope_holidays_dict = {}
    for employee, day in hope_holidays:
        if employee not in hope_holidays_dict:
            hope_holidays_dict[employee] = []
        hope_holidays_dict[employee].append((start_date + timedelta(days=day - 1)).strftime('%Y-%m-%d'))

    iterations = 0
    while iterations < max_iterations:
        shift_table = {employee: [] for employee in employee_capabilities}
        employee_holidays = {employee: 0 for employee in employee_capabilities}
        consecutive_work_days = {employee: 0 for employee in employee_capabilities}

        for i, date in enumerate(date_list):
            date_str = date.strftime('%Y-%m-%d')

            if date_str in holidays:
                required_workers = 5
                possible_tasks = ['M01h', 'M02', 'M03', 'M04', 'M05']
            elif date.weekday() == 5:
                required_workers = 6
                possible_tasks = ['MS', 'M01h' , 'M02', 'M03', 'M04', 'M05']
            elif date.weekday() == 6:
                required_workers = 5
                possible_tasks = ['M01h', 'M02', 'M03', 'M04', 'M05']
            elif date.weekday() == 0:
                required_workers = 11
                possible_tasks = ['771', '772', '773', '774', '775', '776', '777', 'OW', 'M01', 'M02', 'M03', 'M05']
            else:
                required_workers = 11
                possible_tasks = ['771', '772', '773', '774', '775', '776', '777', 'OW', 'MS', 'M02', 'M04', 'M05' ]

            if i >= 3 and all((date_list[i-j].strftime('%Y-%m-%d') in holidays or date_list[i-j].weekday() >= 5) for j in range(1, 4)):
                required_workers = 15
                possible_tasks = ['771', '772', '773', '774', '775', '776', '777', 'OW', 'MS', 'M02', 'M03', 'M05', 'F']
            
            day_tasks = set()
            employees = list(employee_capabilities.keys())
            random.shuffle(employees)

            for employee in employees:
                if i > 0 and shift_table[employee][i-1] == 'M05':
                    shift_table[employee].append('') 
                    employee_holidays[employee] += 1
                    consecutive_work_days[employee] = 0
                    continue

                if employee in hope_holidays_dict and date_str in hope_holidays_dict[employee]:
                    shift_table[employee].append('RH')
                    employee_holidays[employee] += 1
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
                    employee_holidays[employee] += 1
                    consecutive_work_days[employee] = 0

            if len(day_tasks) < required_workers:
                for employee in shift_table.keys():
                    if date_str in hope_holidays_dict.get(employee, []):
                        shift_table[employee][-1] = 'NG'

        if check_employee_holidays(employee_holidays, required_holidays):
            break
        iterations += 1

    return shift_table

# --- [ルーティング設定] Webアプリ用の処理 ---

# デフォルトの社員データ（初期表示用）
DEFAULT_CAPABILITIES = "A,771,775; B,773,774,775,M01,M05; C,773,774,776,777,M01h,M01,M02,M03; D,774,776,777,M03; E,773,774,776,777,M02,M03; F,771,773,775,M01h,M01,M04,M05; G,774; H,771,773,774,775,M01h,M01,M04,M05; I,771,773,774,775,776,777,M01h,M01,M02,M03,M04,M05; J,771,773,M01h,M01,M04,M05; K,OW; L,771,774,776,777,M03; M,M02; N,M02"
DEFAULT_REQUIREMENTS = "A,8; B,8; C,8; D,8; E,8; F,8; G,8; H,8; I,8; J,8; K,8; L,8; M,8; N,8"

@app.route('/', methods=['GET'])
def index():
    # 入力画面を表示
    return render_template('index.html', default_caps=DEFAULT_CAPABILITIES, default_reqs=DEFAULT_REQUIREMENTS)

@app.route('/generate', methods=['POST'])
def generate():
    try:
        # フォームからのデータ受け取り
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

        # 社員能力と休日要件のパース
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

        # シフト生成
        shift_table = generate_shift_table(
            employee_capabilities, start_date, num_days, holidays, required_holidays, hope_holidays
        )

        # Pandasのデータフレームを作成
        df = pd.DataFrame(shift_table)
        df.index = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(len(list(shift_table.values())[0]))]
        df_transposed = df.transpose()

        # サーバーにファイルを保存せず、メモリ上のバッファにExcelを書き出す（Webアプリの鉄板処理）
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_transposed.to_excel(writer, sheet_name='ShiftTable')
        output.seek(0)

        # ユーザーにダウンロードさせる
        filename = f"shift_{start_date_str}.xlsx"
        return send_file(output, as_attachment=True, download_name=filename, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        return f"エラーが発生しました: {str(e)}", 400

if __name__ == '__main__':
    app.run(debug=True)