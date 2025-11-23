import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model
import io
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

# --- [0] 페이지 기본 설정 (가장 먼저 실행되어야 함) ---
st.set_page_config(layout="wide", page_title="ホテルシフト自動作成 Pro")

# --- [🔒 보안] 비밀번호 설정 ---
# 원하는 비밀번호로 변경하세요!
SECRET_PASSWORD = "1234" 

def check_password():
    """비밀번호 확인 함수"""
    def password_entered():
        if st.session_state["password"] == SECRET_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # 입력된 비밀번호 삭제 (보안)
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 처음 접속 시
        st.text_input("パスワードを入力してください (Password)", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # 비밀번호 틀렸을 때
        st.text_input("パスワードを入力してください (Password)", type="password", on_change=password_entered, key="password")
        st.error("パスワードが間違っています。 (Incorrect Password)")
        return False
    else:
        # 비밀번호 맞음
        return True

# 로그인이 안 되어 있으면 여기서 멈춤 (내용 숨김)
if not check_password():
    st.stop()

# --- 로그인 성공 시 아래 내용 실행 ---

# --- 1. 기초 데이터 및 초기 설정 ---
if 'init_done' not in st.session_state:
    st.session_state['shifts_day'] = ['E1', 'E2', 'G1', 'G1U', 'H1', 'H2', 'I1', 'I2', 'L1']
    st.session_state['shifts_night'] = ['Q1', 'Y1', 'R1']
    st.session_state['init_done'] = True

# 스태프 초기 DB
INITIAL_STAFF_DB = [
    {"name": "井戸", "gender": "M", "role": "Manager", "target_off": 8, "skills": "日, G1, H1, Y1, 明"},
    {"name": "畑瀬", "gender": "M", "role": "Manager", "target_off": 8, "skills": "日, G1, H1, Q1, Y1, 明"},
    {"name": "夏川", "gender": "F", "role": "Manager", "target_off": 8, "skills": "E1"},
    {"name": "都筑", "gender": "M", "role": "Manager", "target_off": 8, "skills": "日, G1, H1, Y1, 明"}, 
    {"name": "山口", "gender": "M", "role": "Manager", "target_off": 8, "skills": "日, G1, H1, Y1, 明"},
    {"name": "茅島", "gender": "F", "role": "Staff", "target_off": 8, "skills": "日, G1U, H1, I1, I2, Q1, Y1, 明"},
    {"name": "馬場", "gender": "F", "role": "Staff", "target_off": 8, "skills": "日, G1U, H1, I1, I2, Q1, 明"},
    {"name": "池田", "gender": "F", "role": "Staff", "target_off": 8, "skills": "日, G1U, H1, H2, I1, I2, L1, Q1, 明"},
    {"name": "川野", "gender": "F", "role": "Staff", "target_off": 8, "skills": "日, G1U, H1, H2, I1, I2, Q1, 明"},
    {"name": "加藤", "gender": "F", "role": "Staff", "target_off": 8, "skills": "日, G1U, H1, H2, I1, I2, L1, Q1, 明"},
    {"name": "四ヶ所", "gender": "F", "role": "Staff", "target_off": 8, "skills": "日, G1U, H1, H2, I1, I2, L1, R1, 明"},
    {"name": "朴", "gender": "M", "role": "Staff", "target_off": 8, "skills": "日, G1U, H1, H2, I1, I2, L1, Y1, R1, 明"}, 
    {"name": "ハマノ", "gender": "F", "role": "Staff", "target_off": 8, "skills": "日, G1U, H1, H2, I1, I2, L1"},
    {"name": "田中", "gender": "M", "role": "Staff", "target_off": 8, "skills": "日, G1U, H1, H2, I1, I2, L1, R1, 明"},
    {"name": "市之瀬", "gender": "F", "role": "Staff", "target_off": 8, "skills": "日, G1U, H1, H2, I1, I2, L1, R1, 明"},
    {"name": "鬼塚", "gender": "F", "role": "Staff", "target_off": 8, "skills": "日, G1U, H1, H2, I1, I2"},
    {"name": "春山", "gender": "F", "role": "Staff", "target_off": 8, "skills": "日, G1U, H1, H2, I1, I2, L1"},
    {"name": "佐伯", "gender": "F", "role": "Staff", "target_off": 8, "skills": "E2"},
    {"name": "杉浦", "gender": "F", "role": "Staff", "target_off": 8, "skills": "日, G1U, H1, H2, I1, I2, L1"},
    {"name": "坂田", "gender": "F", "role": "Staff", "target_off": 8, "skills": "L1"},
    {"name": "野田", "gender": "F", "role": "Staff", "target_off": 8, "skills": "E1"},
]

# --- 엑셀 스타일링 함수 ---
def create_styled_excel(df_shift, df_summary):
    wb = Workbook()
    
    # 1. 시프트 시트
    ws_shift = wb.active
    ws_shift.title = "Shift"
    for r in dataframe_to_rows(df_shift, index=False, header=True):
        ws_shift.append(r)
        
    fill_off = PatternFill(start_color="F0F2F6", end_color="F0F2F6", fill_type="solid")
    fill_night = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")
    fill_myong = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
    fill_l1 = PatternFill(start_color="E1BEE7", end_color="E1BEE7", fill_type="solid")
    fill_nichi = PatternFill(start_color="C8E6C9", end_color="C8E6C9", fill_type="solid")
    
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    center_align = Alignment(horizontal='center', vertical='center')

    night_codes = st.session_state['shifts_night']
    
    for row in ws_shift.iter_rows(min_row=1, max_row=ws_shift.max_row, min_col=1, max_col=ws_shift.max_column):
        for cell in row:
            cell.alignment = center_align
            cell.border = thin_border
            val = str(cell.value)
            
            if cell.row == 1:
                cell.font = Font(bold=True)
                continue
                
            if val == 'OFF':
                cell.fill = fill_off
                cell.font = Font(color="BDC3C7")
            elif val in night_codes:
                cell.fill = fill_night
                cell.font = Font(color="B71C1C")
            elif val == '明':
                cell.fill = fill_myong
                cell.font = Font(color="F57F17")
            elif val == 'L1':
                cell.fill = fill_l1
            elif val == '日':
                cell.fill = fill_nichi
                cell.font = Font(bold=True)

    # 2. 요약 시트
    ws_summary = wb.create_sheet("Summary")
    for r in dataframe_to_rows(df_summary, index=False, header=True):
        ws_summary.append(r)
        
    fill_alert = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
    
    for row in ws_summary.iter_rows(min_row=2, max_row=ws_summary.max_row, min_col=2, max_col=ws_summary.max_column):
        for cell in row:
            cell.alignment = center_align
            cell.border = thin_border
            if cell.value == 0:
                cell.fill = fill_alert
                cell.font = Font(color="FF0000", bold=True)

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


# --- 2. 솔버 엔진 ---
def solve_shift(num_days, year, month, prev_history, requests, staff_data, shifts_day, shifts_night):
    model = cp_model.CpModel()
    ALL_SHIFTS = shifts_day + shifts_night + ['日', '明', 'OFF']
    staff_indices = range(len(staff_data))
    days_indices = range(num_days)
    
    manager_indices = [i for i, s in enumerate(staff_data) if s['role'] == 'Manager']
    male_indices = [i for i, s in enumerate(staff_data) if s['gender'] == 'M']
    female_indices = [i for i, s in enumerate(staff_data) if s['gender'] == 'F']
    
    shifts = {}
    for s in staff_indices:
        for d in days_indices:
            for code in ALL_SHIFTS:
                shifts[(s, d, code)] = model.NewBoolVar(f'shift_s{s}_d{d}_{code}')

    # --- [1] 전달 기록 처리 ---
    for s_idx, staff in enumerate(staff_data):
        name = staff['name']
        h_d1 = prev_history.get(name, {}).get('d-1', 'OFF')
        h_d2 = prev_history.get(name, {}).get('d-2', 'OFF')
        h_d3 = prev_history.get(name, {}).get('d-3', 'OFF')
        
        if pd.isna(h_d1) or h_d1 == '': h_d1 = 'OFF'
        if pd.isna(h_d2) or h_d2 == '': h_d2 = 'OFF'
        if pd.isna(h_d3) or h_d3 == '': h_d3 = 'OFF'

        if h_d1 in shifts_night:
            model.Add(shifts[(s_idx, 0, '明')] == 1)
        if h_d1 == '明':
            model.Add(shifts[(s_idx, 0, 'OFF')] == 1)

        w_d3 = 1 if h_d3 != 'OFF' else 0
        w_d2 = 1 if h_d2 != 'OFF' else 0
        w_d1 = 1 if h_d1 != 'OFF' else 0
        
        c0 = 1 - shifts[(s_idx, 0, 'OFF')] if 0 < num_days else 0
        c1 = 1 - shifts[(s_idx, 1, 'OFF')] if 1 < num_days else 0
        c2 = 1 - shifts[(s_idx, 2, 'OFF')] if 2 < num_days else 0
        c3 = 1 - shifts[(s_idx, 3, 'OFF')] if 3 < num_days else 0

        model.Add(w_d3 + w_d2 + w_d1 + c0 + c1 <= 4)
        if num_days >= 3:
            model.Add(w_d2 + w_d1 + c0 + c1 + c2 <= 4)
        if num_days >= 4:
            model.Add(w_d1 + c0 + c1 + c2 + c3 <= 4)

    # --- [2] Hard Constraints ---
    for s in staff_indices:
        for d in days_indices:
            model.Add(sum(shifts[(s, d, c)] for c in ALL_SHIFTS) == 1)

    for s in staff_indices:
        skill_str = staff_data[s]['skills']
        skill_list = [x.strip() for x in str(skill_str).split(',')]
        allowed = skill_list + ['OFF']
        for d in days_indices:
            for code in ALL_SHIFTS:
                if code not in allowed:
                    model.Add(shifts[(s, d, code)] == 0)

    for s in staff_indices:
        for d in range(num_days - 1):
            is_night = sum(shifts[(s, d, c)] for c in shifts_night)
            model.Add(shifts[(s, d + 1, '明')] == is_night)

    for s in staff_indices:
        for d in range(num_days - 1):
             model.AddImplication(shifts[(s, d, '明')], shifts[(s, d + 1, 'OFF')])

    for s in staff_indices:
        for d in range(num_days - 4):
            works = [1 - shifts[(s, d + k, 'OFF')] for k in range(5)]
            model.Add(sum(works) <= 4)
    
    ido_idx = next((i for i, s in enumerate(staff_data) if s['name'] == '井戸'), None)
    for s in staff_indices:
        if s != ido_idx:
            for d in days_indices:
                staff_name = staff_data[s]['name']
                is_requested_nichi = False
                if staff_name in requests and (d+1) in requests[staff_name]:
                    if requests[staff_name][d+1] == '日':
                        is_requested_nichi = True
                if not is_requested_nichi:
                    model.Add(shifts[(s, d, '日')] == 0)

    # 근무 시간 순서 (Inter-shift Interval)
    SHIFT_TIME_RANK = {
        'E1': 0, 'E2': 1, 
        'G1': 2, 'G1U': 2, '日': 2,
        'H1': 3, 'H2': 4, 
        'I1': 5, 'I2': 6, 
        'L1': 7
    }
    
    for s in staff_indices:
        for d in range(num_days - 1):
            for prev_code, prev_rank in SHIFT_TIME_RANK.items():
                for next_code, next_rank in SHIFT_TIME_RANK.items():
                    if next_rank < prev_rank - 1:
                        if prev_code in ALL_SHIFTS and next_code in ALL_SHIFTS:
                            model.AddImplication(shifts[(s, d, prev_code)], shifts[(s, d+1, next_code)].Not())

    for s in staff_indices:
        for d in range(num_days - 1):
            restricted_next_days = ['E1', 'E2', 'G1', 'G1U', 'H1', 'H2', 'I1', 'I2', '日']
            for bad_next in restricted_next_days:
                if bad_next in ALL_SHIFTS:
                    model.AddImplication(shifts[(s, d, 'L1')], shifts[(s, d+1, bad_next)].Not())


    # --- [3] Soft Constraints ---
    penalties = []
    fixed_codes = shifts_night + ['L1']
    for d in days_indices:
        for code in fixed_codes:
            if code in ALL_SHIFTS:
                count = sum(shifts[(s, d, code)] for s in staff_indices)
                diff = model.NewIntVar(-len(staff_indices), len(staff_indices), f'diff_{d}_{code}')
                model.Add(diff == count - 1)
                abs_diff = model.NewIntVar(0, len(staff_indices), f'abs_diff_{d}_{code}')
                model.AddAbsEquality(abs_diff, diff)
                penalties.append(abs_diff * 1000000)

    flexible_day_codes = [c for c in shifts_day if c != 'L1']
    for d in days_indices:
        for code in flexible_day_codes:
            if code in ALL_SHIFTS:
                count = sum(shifts[(s, d, code)] for s in staff_indices)
                is_zero = model.NewBoolVar(f'is_zero_{d}_{code}')
                model.Add(count == 0).OnlyEnforceIf(is_zero)
                model.Add(count > 0).OnlyEnforceIf(is_zero.Not())
                penalties.append(is_zero * 5000)

    for d in days_indices:
        manager_count = sum(shifts[(s, d, c)] for s in manager_indices for c in shifts_day)
        is_m_zero = model.NewBoolVar(f'is_m_zero_{d}')
        model.Add(manager_count == 0).OnlyEnforceIf(is_m_zero)
        model.Add(manager_count > 0).OnlyEnforceIf(is_m_zero.Not())
        penalties.append(is_m_zero * 50000)

    for d in days_indices:
        manager_night_count = sum(shifts[(s, d, c)] for s in manager_indices for c in shifts_night)
        is_m_night_over = model.NewBoolVar(f'is_m_night_over_{d}')
        model.Add(manager_night_count > 1).OnlyEnforceIf(is_m_night_over)
        model.Add(manager_night_count <= 1).OnlyEnforceIf(is_m_night_over.Not())
        penalties.append(is_m_night_over * 50000)

    park_idx = next((i for i, s in enumerate(staff_data) if s['name'] == '朴'), None)
    if park_idx is not None:
        for d in days_indices:
            penalties.append(-300 * shifts[(park_idx, d, 'Y1')])
            penalties.append(50 * shifts[(park_idx, d, 'R1')])

    for d in days_indices:
        for s in male_indices:
             for c in shifts_night:
                 penalties.append(-50 * shifts[(s, d, c)])

    tsuzuki_idx = next((i for i, s in enumerate(staff_data) if s['name'] == '都筑'), None)
    if tsuzuki_idx is not None:
        for d in days_indices:
            for c in shifts_night:
                penalties.append(-200 * shifts[(tsuzuki_idx, d, c)])

    for s in female_indices:
        skill_list = [x.strip() for x in str(staff_data[s]['skills']).split(',')]
        if 'Y1' in skill_list:
            for d in days_indices:
                penalties.append(200 * shifts[(s, d, 'Y1')])

    for s in staff_indices:
        for d in range(num_days - 2):
            off1 = shifts[(s, d, 'OFF')]
            off2 = shifts[(s, d + 1, 'OFF')]
            off3 = shifts[(s, d + 2, 'OFF')]
            is_2_consecutive = model.NewBoolVar(f'cons_2_off_{s}_{d}')
            model.AddBoolAnd([off1, off2]).OnlyEnforceIf(is_2_consecutive)
            model.AddBoolOr([off1.Not(), off2.Not()]).OnlyEnforceIf(is_2_consecutive.Not())
            penalties.append(-30 * is_2_consecutive)
            is_3_consecutive = model.NewBoolVar(f'cons_3_off_{s}_{d}')
            model.AddBoolAnd([off1, off2, off3]).OnlyEnforceIf(is_3_consecutive)
            model.AddBoolOr([off1.Not(), off2.Not(), off3.Not()]).OnlyEnforceIf(is_3_consecutive.Not())
            penalties.append(500 * is_3_consecutive)

    # (7) 개인별 휴일 수 강제
    for s in staff_indices:
        name = staff_data[s]['name']
        target_off_count = staff_data[s]['target_off']
        if pd.isna(target_off_count): target_off_count = 8
        requested_offs = 0
        if name in requests:
            requested_offs = sum(1 for code in requests[name].values() if code == 'OFF')
        final_target = int(max(target_off_count, requested_offs))
        actual_offs = model.NewIntVar(0, num_days, f'off_count_{s}')
        model.Add(actual_offs == sum(shifts[(s, d, 'OFF')] for d in days_indices))
        diff = model.NewIntVar(0, num_days, f'off_diff_{s}')
        model.AddAbsEquality(diff, actual_offs - final_target)
        penalties.append(diff * 100000)

    # (8) 희망 근무
    for s_idx, staff in enumerate(staff_data):
        name = staff['name']
        if name in requests:
            for day, req_code in requests[name].items():
                if 1 <= day <= num_days:
                    target_var = shifts[(s_idx, day-1, req_code)]
                    penalties.append((1 - target_var) * 1000000)

    model.Minimize(sum(penalties))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        st.success(f"✅ シフト作成完了！ (状態: {solver.StatusName(status)})")
        schedule_data = []
        for s in staff_indices:
            row = {'Staff': staff_data[s]['name']}
            total_off = 0
            for d in days_indices:
                if solver.Value(shifts[(s, d, 'OFF')]):
                    total_off += 1
            row['公休数'] = total_off
            for d in days_indices:
                found = False
                for code in ALL_SHIFTS:
                    if solver.Value(shifts[(s, d, code)]):
                        row[f'{d+1}日'] = code
                        found = True
                        break
                if not found: row[f'{d+1}日'] = "ERR"
            schedule_data.append(row)
        
        df_result = pd.DataFrame(schedule_data)
        
        daily_summary_list = []
        for d in days_indices:
            day_col = f'{d+1}日'
            day_stats = {'日付': day_col}
            
            mgr_day_count = 0
            mgr_night_count = 0
            for s_idx, staff in enumerate(staff_data):
                val = df_result.iloc[s_idx][day_col]
                if staff['role'] == 'Manager':
                    if val in shifts_day: mgr_day_count += 1
                    if val in shifts_night: mgr_night_count += 1
            
            day_stats['Manager(昼)'] = mgr_day_count
            day_stats['Manager(夜)'] = mgr_night_count
            
            codes_to_track = shifts_night + shifts_day + ['OFF', '日', '明']
            for code in codes_to_track:
                if code in ALL_SHIFTS:
                    cnt = sum(1 for s_idx in staff_indices if df_result.iloc[s_idx][day_col] == code)
                    day_stats[code] = cnt
            daily_summary_list.append(day_stats)
            
        df_summary = pd.DataFrame(daily_summary_list)
        return df_result, df_summary
    else:
        st.error("❌ 作成失敗 (条件不一致)")
        return None, None

# --- 3. Streamlit UI ---
st.title("🏨 ホテルシフト自動作成 (Final Ver.)")

with st.sidebar:
    st.header("⚙️ システム設定")
    if st.button("ログアウト (Logout)"):
        del st.session_state["password_correct"]
        st.rerun()
        
    st.header("📅 日付設定")
    col1, col2 = st.columns(2)
    year = col1.number_input("年", 2025, 2030, 2025)
    month = col2.number_input("月", 1, 12, 11)
    days_in_month = pd.Period(f"{year}-{month}").days_in_month
    st.info(f"計 {days_in_month}日")

with st.expander("⚙️ 勤務コード設定（新しい時間帯の追加・削除）"):
    st.caption("例: Z1, Z2 のようにカンマ区切りで入力してください。")
    c1, c2 = st.columns(2)
    day_shifts_str = c1.text_area("日勤コード", ", ".join(st.session_state['shifts_day']))
    night_shifts_str = c2.text_area("夜勤コード", ", ".join(st.session_state['shifts_night']))
    
    st.session_state['shifts_day'] = [x.strip() for x in day_shifts_str.split(',') if x.strip()]
    st.session_state['shifts_night'] = [x.strip() for x in night_shifts_str.split(',') if x.strip()]
    
    DROPDOWN_OPTIONS = [''] + ['OFF', '日', '明'] + st.session_state['shifts_night'] + st.session_state['shifts_day']

with st.expander("👥 スタッフ管理（目標休日＆可能勤務の編集）", expanded=True):
    st.write("各スタッフの **目標公休数** と **可能勤務** を編集できます。")
    df_staff = pd.DataFrame(INITIAL_STAFF_DB)
    edited_staff_df = st.data_editor(
        df_staff,
        num_rows="dynamic",
        column_config={
            "target_off": st.column_config.NumberColumn("目標公休数", min_value=0, max_value=31, step=1),
            "skills": st.column_config.TextColumn("可能勤務 (カンマ区切り)", width="large"),
            "role": st.column_config.SelectboxColumn("役職", options=["Manager", "Staff"]),
             "gender": st.column_config.SelectboxColumn("性別", options=["M", "F"])
        },
        use_container_width=True
    )

with st.expander("🔙 前月の最後3日間の勤務入力 (CSVアップロード対応)"):
    uploaded_prev = st.file_uploader("CSVファイルで一括アップロード (前月記録)", type=['csv'])
    prev_cols = ['d-3', 'd-2', 'd-1']
    current_names = edited_staff_df['name'].tolist() if 'name' in edited_staff_df.columns else []
    
    if current_names:
        init_prev = pd.DataFrame(index=current_names, columns=prev_cols)
        if uploaded_prev is not None:
            try:
                df_upload_prev = pd.read_csv(uploaded_prev, index_col=0)
                init_prev.update(df_upload_prev)
                st.success("CSVアップロード完了！")
            except Exception as e:
                st.error(f"CSV読み込みエラー: {e}")

        prev_column_config = {
            col: st.column_config.SelectboxColumn(col, width="small", options=DROPDOWN_OPTIONS, required=False)
            for col in prev_cols
        }
        prev_editor = st.data_editor(init_prev, column_config=prev_column_config, num_rows="fixed")
        csv_template_prev = init_prev.to_csv().encode('utf-8')
        st.download_button("📥 テンプレートをダウンロード (CSV)", csv_template_prev, "prev_history_template.csv")
    else:
        st.warning("スタッフリストが空です。")
        prev_editor = pd.DataFrame()

# --- 메인 탭 ---
tab1, tab2 = st.tabs(["📋 希望シフト入力", "📅 結果確認"])

with tab1:
    st.info("💡 CSVアップロード、またはセルをクリックして選択してください。")
    uploaded_req = st.file_uploader("CSVファイルで一括アップロード (希望シフト)", type=['csv'])

    if current_names:
        init_data = pd.DataFrame(index=current_names, columns=[f'{i}日' for i in range(1, days_in_month+1)])
        if uploaded_req is not None:
            try:
                df_upload_req = pd.read_csv(uploaded_req, index_col=0)
                init_data.update(df_upload_req)
                st.success("CSVアップロード完了！")
            except Exception as e:
                st.error(f"CSV読み込みエラー: {e}")

        request_column_config = {
            col: st.column_config.SelectboxColumn(col, width="small", options=DROPDOWN_OPTIONS, required=False)
            for col in init_data.columns
        }
        edited_schedule = st.data_editor(init_data, column_config=request_column_config, num_rows="fixed", height=500)
        csv_template_req = init_data.to_csv().encode('utf-8')
        st.download_button("📥 テンプレートをダウンロード (CSV)", csv_template_req, "request_shift_template.csv")
    else:
        st.warning("スタッフリストが空です。")
        edited_schedule = pd.DataFrame()

with tab2:
    if st.button("🚀 シフト作成開始", type="primary"):
        if edited_staff_df.empty:
            st.error("スタッフデータがありません。")
        else:
            staff_data = edited_staff_df.to_dict('records')

            prev_history = {}
            if not prev_editor.empty:
                for staff_name in prev_editor.index:
                    prev_history[staff_name] = {}
                    for col in prev_cols:
                        val = prev_editor.loc[staff_name, col]
                        if pd.notna(val) and val != "":
                            prev_history[staff_name][col] = val
                        else:
                            prev_history[staff_name][col] = 'OFF'

            requests = {}
            if not edited_schedule.empty:
                for staff_name in edited_schedule.index:
                    requests[staff_name] = {}
                    for day_col in edited_schedule.columns:
                        val = edited_schedule.loc[staff_name, day_col]
                        if pd.notna(val) and val != "":
                            day_num = int(day_col.replace('日', ''))
                            requests[staff_name][day_num] = val

            with st.spinner("最適なシフトを計算中..."):
                result_df, summary_df = solve_shift(
                    days_in_month, year, month, 
                    prev_history, requests, staff_data,
                    st.session_state['shifts_day'], st.session_state['shifts_night']
                )

            if result_df is not None:
                st.write("### 📅 スタッフ別シフト表")
                def color_shift(val):
                    if isinstance(val, int): return ''
                    bg_color = 'white'; text_color = 'black'
                    if val == 'OFF': bg_color = '#f0f2f6'; text_color = '#bdc3c7'
                    elif val in st.session_state['shifts_night']: bg_color = '#ffcdd2'; text_color = '#b71c1c'
                    elif val == '明': bg_color = '#fff9c4'; text_color = '#f57f17'
                    elif val == 'L1': bg_color = '#e1bee7'
                    elif val == '日': bg_color = '#c8e6c9'; return f'background-color: {bg_color}; color: {text_color}; font-weight: bold; border: 1px solid #eee;'
                    return f'background-color: {bg_color}; color: {text_color}; text-align: center; border: 1px solid #eee;'

                st.dataframe(result_df.style.applymap(color_shift), height=1200, use_container_width=True)
                
                st.divider()
                st.write("### 📊 日別集計ダッシュボード (人員不足確認)")
                st.info("0名の箇所は赤色で表示されます。")
                
                def highlight_zero(val):
                    if isinstance(val, int) and val == 0:
                        return 'background-color: #ffcccc; color: red; font-weight: bold;'
                    return ''
                
                st.dataframe(summary_df.style.applymap(highlight_zero, subset=summary_df.columns[1:]), height=400, use_container_width=True)

                excel_data = create_styled_excel(result_df, summary_df)
                st.download_button("📥 Excelダウンロード (色付き・集計表含む)", excel_data, f"{year}_{month}_shift_styled.xlsx")

                st.write("")
                st.write("")
                st.write("")
                st.write("---")
                st.caption("Generated by Hotel Shift Manager Pro")
                st.write("<br><br><br>", unsafe_allow_html=True)