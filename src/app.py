"""
🚀 CORE AGENT APP (Dành cho Role 4: Core Agent Developer)
File chính ghép nối tất cả các thành phần: Tools + Prompts + Test Cases + Multi-Provider.
"""

import json
import os
import sys
from dotenv import load_dotenv

# Đảm bảo import các module cùng thư mục src/ hoạt động mượt mà
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Import các thành phần từ file của Role 2, Role 3 & Multi-Provider Adapter
from tools import AVAILABLE_TOOLS
from prompts import CHATBOT_BASELINE_PROMPT, REACT_SYSTEM_PROMPT, MAX_ITERATIONS
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Đọc bộ test cases từ config/test_cases.json của Role 1"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    
    # Fallback kiểm tra nếu file ở thư mục hiện tại
    if not os.path.exists(config_path):
        config_path = "test_cases.json"
        
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_baseline_chatbot(user_query: str, provider):
    """
    Dựng Chatbot gốc (Baseline) không có công cụ.
    """
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    print(f"⚙️ System Prompt: {CHATBOT_BASELINE_PROMPT.strip()}")
    
    # Gọi LLM Provider thực hiện sinh câu trả lời
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot trả lời:\n{response}")


def run_react_agent(user_query: str, provider):
    """
    Dựng vòng lặp ReAct Agent (Thought -> Action -> Observation) có Guardrails.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    step = 0
    
    # Khởi tạo scratchpad lưu lịch sử Thought/Action/Observation
    import re
    scratchpad = f"Question: {user_query}\n"
    
    while step < MAX_ITERATIONS:
        step += 1
        print(f"\n--- 🔄 Vòng lặp ReAct (Step {step}/{MAX_ITERATIONS}) ---")
        
        # 1. LLM sinh ra Thought/Action (hoặc Final Answer)
        response = provider.generate(scratchpad, system_prompt=REACT_SYSTEM_PROMPT)
        print(f"🤖 LLM Output:\n{response}")
        
        # Ghi nhận vào scratchpad
        scratchpad += f"{response}\n"
        
        # 2. Kiểm tra Final Answer
        if "Final Answer:" in response:
            print("🏁 Agent đã đưa ra câu trả lời cuối cùng!")
            break
            
        # 3. Parse Action
        action_match = re.search(r"Action:\s*(\w+)\[(.*?)\]", response)
        if action_match:
            tool_name = action_match.group(1).strip()
            tool_arg = action_match.group(2).strip()
            
            # Loại bỏ dấu nháy thừa (nếu có) do LLM sinh ra
            if (tool_arg.startswith("'") and tool_arg.endswith("'")) or (tool_arg.startswith('"') and tool_arg.endswith('"')):
                tool_arg = tool_arg[1:-1]
                
            print(f"🛠️ Thực thi Tool: {tool_name} với tham số: '{tool_arg}'")
            
            # Gọi hàm tool
            if tool_name in AVAILABLE_TOOLS:
                tool_func = AVAILABLE_TOOLS[tool_name]
                try:
                    # Hỗ trợ truyền nhiều tham số nếu có dấu phẩy
                    if "," in tool_arg:
                        args = [arg.strip(" '\"") for arg in tool_arg.split(",", 1)]
                        obs = tool_func(*args)
                    else:
                        obs = tool_func(tool_arg)
                except Exception as e:
                    obs = f"Lỗi thực thi tool: {str(e)}"
            else:
                obs = f"Lỗi: Không tìm thấy công cụ '{tool_name}'."
                
            print(f"👁️ Observation: {obs}")
            
            # Ghi Observation vào scratchpad để LLM phân tích ở bước tiếp theo
            scratchpad += f"Observation: {obs}\n"
            
        else:
            print("⚠️ Không tìm thấy Action hợp lệ hoặc Final Answer. Dừng lặp để an toàn.")
            break
            
    if step >= MAX_ITERATIONS:
        print(f"🛡️ GUARDRAIL TRIGGERED: Đã đạt giới hạn tối đa {MAX_ITERATIONS} bước. Ngắt lặp an toàn!")


if __name__ == "__main__":
    print("==================================================")
    print("🏫 ĐẠI HỌC VINUNI - BÀI LAB 3: CHATBOT VS REACT AGENT")
    print("==================================================")
    
    # Khởi tạo Multi-Provider LLM Adapter (Đọc từ biến môi trường LLM_PROVIDER)
    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    print(f"🔌 LLM Provider đang hoạt động: {provider.__class__.__name__} (Model: {model_name})")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases từ config/test_cases.json\n")
    
    print("--- DEMO 1: CHẠY TRÊN CHATBOT BASELINE ---")
    for test in tests:
        print(f"\n[Test Case {test['id']}] {test['category']}")
        run_baseline_chatbot(test["question"], provider)
        print("-" * 50)
    
    # Chạy thử câu test số 3 cho React Agent
    sample_query = tests[2]["question"]
    print("\n--- DEMO 2: CHẠY TRÊN REACT AGENT ---")
    run_react_agent(sample_query, provider)
