import streamlit as st
from urllib.parse import urlparse, parse_qs
import json

st.set_page_config(page_title="HTTP Request Analyzer", page_icon="📡")

st.title("📡 HTTP 요청 전문 분석 & 재현 도구")

raw_request = st.text_area(
    "📝 Raw HTTP 요청 입력", 
    height=300, 
    placeholder="POST /download HTTP/1.1\nHost: example.com\nContent-Type: application/x-www-form-urlencoded\n...\nfilename=important.pdf&dir=../../.."
)

if st.button("🔍 분석하기"):
    if not raw_request.strip():
        st.warning("요청 전문을 입력해주세요.")
    else:
        try:
            # ------------------------------------
            # 1️⃣ 기본 파싱 (메서드, 경로, 헤더, 바디)
            # ------------------------------------
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

            # ------------------------------------
            # 2️⃣ 파라미터 추출 (GET & POST)
            # ------------------------------------
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

            # ------------------------------------
            # 3️⃣ 결과 요약 문자열 생성
            # ------------------------------------
            request_summary = f"{method} {raw_path}"
            host = headers.get("Host", "-")
            params_str = (
                "-" if not params else ", ".join([f"{k}={v}" for k, v in params.items()])
            )
            summary_text = f"{request_summary}\nHost: {host}\nParams: {params_str}"

            # ------------------------------------
            # 4️⃣ cURL 명령어 생성
            # ------------------------------------
            scheme = "https"  # 기본값. 필요 시 사용자가 수정.
            url = f"{scheme}://{host}{raw_path}"

            curl_parts = [f"curl -X {method} \"{url}\""]

            # 포함할 헤더 (Host 제외)
            include_headers = [
                key for key in headers.keys() if key.lower() not in ["host", "content-length"]
            ]
            for h in include_headers:
                curl_parts.append(f"  -H \"{h}: {headers[h]}\"")

            # Body
            if body:
                curl_parts.append(f"  --data-raw '{body}'")

            curl_cmd = " \\\n".join(curl_parts)

            # ------------------------------------
            # 5️⃣ 출력 (요약 & cURL)
            # ------------------------------------
            st.subheader("📋 분석 결과 (복사 아이콘 사용)")
            st.code(summary_text, language="")

            st.subheader("🔄 재현용 cURL")
            st.code(curl_cmd, language="bash")

            # ------------------------------------
            # 6️⃣ Notion 테이블용 Markdown (선택)
            # ------------------------------------
            if params:
                st.subheader("🔗 Notion 테이블용 Markdown")
                md_rows = ["| 파라미터 | 값 |", "|---|---|"]
                for k, v in params.items():
                    md_rows.append(f"| {k} | {v} |")
                notion_md = "\n".join(md_rows)
                st.code(notion_md, language="markdown")
                st.caption("위 표를 복사해 Notion 등에 붙여넣으세요.")

        except Exception as e:
            st.error(f"분석 중 오류: {str(e)}")
