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

def generate_shift_table(employee_capabilities, start_date, num_days, holidays, required_holidays, hope_holidays, max_iterations=1000):
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
    # Renderのタイムアウトを避けるため、最外周の最大試行回数を1000回に制限
    while iterations < max_iterations:
        shift_table = {employee: [] for employee in employee_capabilities}
        employee_holidays = {employee: 0 for employee in employee_capabilities}
        consecutive_work_days = {employee: 0 for employee in employee_capabilities}
        
        all_days_success = True  # 全日程が正常に組めたかどうかのフラグ

        for i, date in enumerate(date_list):
            date_str = date.strftime('%Y-%m-%d')

            if date_str in holidays:
                required_workers = 5
                possible_tasks = ['M01','M02', 'M03', 'M04', 'M05']
            elif date.weekday() == 5:
                required_workers = 6
                possible_tasks = ['M01', 'HM' , 'M02', 'M03', 'M04', 'M05']
            elif date.weekday() == 6:
                required_workers = 6
                possible_tasks = ['M01','HM' ,'M02', 'M03', 'M04', 'M05']
            elif date.weekday() == 0:
                required_workers = 11
                possible_tasks = ['771', '772', '773', '774', '775', '776', '777','M01', 'M02', 'M04', 'M05']
            else:
                required_workers = 11
                possible_tasks = ['771', '772', '773', '774', '775', '776', '777', 'M01', 'M02', 'M04', 'M05' ]

            # --- その日のシフトを埋めるためのローカル試行（最大50回） ---
            day_success = False
            for _ in range(50):
                day_tasks = set()
                # 試行ごとに一時的な状態をリセットしてやり直す
                temp_shifts = {}
                temp_holidays = employee_holidays.copy()
                temp_consecutive = consecutive_work_days.copy()

                employees = list(employee_capabilities.keys())
                random.shuffle(employees)

                for employee in employees:
                    # 前日M05の休み処理
                    if i > 0 and shift_table[employee][i-1] == 'M05':
                        temp_shifts[employee] = ''
                        temp_holidays[employee] += 1
                        temp_consecutive[employee] = 0
                        continue

                    # 希望休の処理
                    if employee in hope_holidays_dict and date_str in hope_holidays_dict[employee]:
                        temp_shifts[employee] = 'RH'
                        temp_holidays[employee] += 1
                        temp_consecutive[employee] = 0
                    # 必要人数に達していない ＆ 5連勤未満なら出勤を検討
                    elif len(day_tasks) < required_workers and temp_consecutive[employee] < 5:
                        possible_employee_tasks = [task for task in employee_capabilities[employee] if task in possible_tasks and task not in day_tasks]
                        if possible_employee_tasks:
                            task = random.choice(possible_employee_tasks)
                            temp_shifts[employee] = task
                            day_tasks.add(task)
                            temp_consecutive[employee] += 1
                        else:
                            temp_shifts[employee] = ''
                            temp_consecutive[employee] = 0
                    else:
                        temp_shifts[employee] = ''
                        temp_holidays[employee] += 1
                        temp_consecutive[employee] = 0

                # 必要人数を無事満たせたら、この日の決定事項とする
                if len(day_tasks) == required_workers:
                    day_success = True
                    # 本番データに反映
                    for emp in employee_capabilities:
                        shift_table[emp].append(temp_shifts[emp])
                    employee_holidays = temp_holidays
                    consecutive_work_days = temp_consecutive
                    break
            
            # 50回シャッフルしてもその日の人数が埋まらなかった場合
            if not day_success:
                all_days_success = False
                break # この周（全日程のやり直し）を諦めて次の iteration へ

        # すべての日程が正常に埋まり、かつ全員の公休数が基準を満たしていれば終了
        if all_days_success and check_employee_holidays(employee_holidays, required_holidays):
            break
            
        iterations += 1

    return shift_table
# --- [ルーティング設定] Webアプリ用の処理 ---

# デフォルトの社員データ（初期表示用）
DEFAULT_CAPABILITIES = "A,773,774,775,M01,HM,M05; B,773,774,776,777,M01,HM,M02,M03,M05; C,773,774,776,777,M03; D,773,774,776,777,M02,M03,M05; E,773,774,775,HM; F,776,777,M02,M03; G,771,772,775,M04; H,771,772,773,774,775,M01,HM,M04,M05; I,771,772,773,774,M01h,M01,HM,M04,M05; J,772,773,775,HM; K,771,774,776,777,M01,M03,HM; L,M02; M,771,772,774,HM,M04; N,771,772"
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