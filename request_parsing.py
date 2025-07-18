import streamlit as st
from streamlit.components.v1 import html
from urllib.parse import urlparse, parse_qs
import json
# pyperclip import 제거
import uuid

st.set_page_config(page_title="HTTP Request Analyzer", page_icon="📡")

st.title("📡 HTTP 요청 전문 분석 & 재현 도구")

def format_cmd_arg(value):
    if '"' in value:
        return f"'{value}'"
    return f'"{value}"'

def render_analysis_result(endpoint, host, params_disp, params):
    st.subheader("📋 분석 결과")
    st.markdown(f"**엔드포인트:** {endpoint}")
    st.markdown(f"**호스트:** {host}")
    st.markdown(f"**==파라미터==**  ")
    st.markdown(params_disp)
    # 파라미터 복사 텍스트를 한 줄씩 개행, 키와 값을 콜론(:)과 공백으로 구분
    if params:
        param_lines = [f"{k} = `{v}`" for k, v in params.items()]
        param_text = "\n".join(param_lines)
    else:
        param_text = "-"
    copy_text = f"**엔드포인트:** {endpoint}\n**호스트:** {host}\n<파라미터> \n{param_text}"

    btn_id = "copy-btn"
    html(f'''
        <style>
        #{btn_id} {{
            background: linear-gradient(90deg, #4f8cff 0%, #235390 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 22px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(79,140,255,0.15);
            transition: background 0.2s, transform 0.1s;
        }}
        #{btn_id}:hover {{
            background: linear-gradient(90deg, #235390 0%, #4f8cff 100%);
            transform: translateY(-2px) scale(1.04);
        }}
        #copy-msg {{
            color: #2ecc40;
            font-weight: 500;
            margin-left: 14px;
            font-size: 1rem;
        }}
        </style>
        <button id="{btn_id}">분석 결과 클립보드로 복사</button>
        <script>
        const btn = document.getElementById("{btn_id}");
        btn.onclick = function() {{
            navigator.clipboard.writeText(`{copy_text.replace("`", "\\`")}`);
            btn.insertAdjacentHTML('afterend', '<span id="copy-msg">클립보드 복사가 완료되었습니다.</span>');
            setTimeout(() => {{
                const msg = document.getElementById("copy-msg");
                if (msg) msg.remove();
            }}, 2000);
        }};
        </script>
    ''', height=60)

def render_curl(curl_cmd):
    st.subheader("🔄 재현용 cURL (Windows CMD 호환)")
    st.code(curl_cmd, language="bash")

def render_notion_md(notion_md):
    if notion_md:
        st.subheader("🔗 Notion 테이블용 Markdown")
        st.code(notion_md, language="markdown")
        st.caption("위 표를 복사해 Notion 등에 붙여넣으세요.")

raw_request = st.text_area(
    "📝 Raw HTTP 요청 입력",
    height=300,
    placeholder=(
        "POST /download HTTP/1.1\n"
        "Host: example.com\n"
        "Content-Type: application/x-www-form-urlencoded\n"
        "...\n"
        "filename=important.pdf&dir=../../.."
    ),
)

if 'show_copy_area' not in st.session_state:
    st.session_state['show_copy_area'] = False

if st.button("🔍 분석하기"):
    # 분석 결과, cURL, Notion 마크다운을 session_state에 저장
    st.session_state['show_copy_area'] = False
    if not raw_request.strip():
        st.warning("요청 전문을 입력해주세요.")
    else:
        try:
            # -----------------------------
            # 1️⃣ 요청 라인 / 헤더 / 바디 파싱
            # -----------------------------
            lines = raw_request.strip().splitlines()
            request_line = lines[0]
            method, raw_path, _ = request_line.split()

            headers = {}
            body_lines = []
            is_body = False
            for line in lines[1:]:
                if is_body:
                    body_lines.append(line)
                elif line.strip() == "":
                    is_body = True
                else:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        headers[k.strip()] = v.strip()

            body = "\n".join(body_lines).strip()

            # -----------------------------
            # 2️⃣ 파라미터 추출 (GET & POST)
            # -----------------------------
            parsed_url = urlparse(raw_path)
            params = {}

            # GET params
            params.update({k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed_url.query).items()})

            content_type = headers.get("Content-Type", "").split(";")[0].strip().lower()

            # POST params
            if body:
                if content_type == "application/json":
                    try:
                        json_data = json.loads(body)
                        if isinstance(json_data, dict):
                            params.update(json_data)
                    except json.JSONDecodeError:
                        pass
                elif content_type == "application/x-www-form-urlencoded":
                    params.update({k: v[0] if len(v) == 1 else v for k, v in parse_qs(body).items()})

            # -----------------------------
            # 3️⃣ 출력용 변수
            # -----------------------------
            host = headers.get("Host", "-")
            endpoint = f"{method} {parsed_url.path}"
            if not params:
                params_disp = "-"
            else:
                # 마크다운용
                params_disp = "  \n".join([f"**{k}** = `{v}`" for k, v in params.items()])

            # -----------------------------
            # 4️⃣ cURL (Windows CMD 호환)
            # -----------------------------
            scheme = "https"  # 필요 시 수정
            url = f"{scheme}://{host}{raw_path}"

            curl_parts = [f'curl -X {method} {format_cmd_arg(url)}']
            for h, v in headers.items():
                if h.lower() in ["host", "content-length"]:
                    continue
                curl_parts.append(f'-H {format_cmd_arg(f"{h}: {v}")}')
            if body:
                safe_body = body.replace("`", "\`")
                curl_parts.append(f'--data-raw {format_cmd_arg(safe_body)}')

            curl_cmd = " ".join(curl_parts)

            # -----------------------------
            # 5️⃣ Notion 테이블용 Markdown
            # -----------------------------
            if params:
                md_rows = ["| 파라미터 | 값 |", "|---|---|"]
                for k, v in params.items():
                    md_rows.append(f"| {k} | {v} |")
                notion_md = "\n".join(md_rows)
            else:
                notion_md = ""

            # -----------------------------
            # 6️⃣ 결과 session_state에 저장
            # -----------------------------
            st.session_state['analysis_result'] = {
                'endpoint': endpoint,
                'host': host,
                'params_disp': params_disp,
                'curl_cmd': curl_cmd,
                'notion_md': notion_md,
                'params': params
            }

        except Exception as e:
            st.error(f"분석 중 오류: {str(e)}")

# session_state에 분석 결과가 있으면 출력
if 'analysis_result' in st.session_state:
    data = st.session_state['analysis_result']
    render_analysis_result(data['endpoint'], data['host'], data['params_disp'], data['params'])
    render_curl(data['curl_cmd'])
    render_notion_md(data['notion_md'])
