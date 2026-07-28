import os
import sys
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import csv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools import AVAILABLE_TOOLS
from prompts import CHATBOT_BASELINE_PROMPT, REACT_SYSTEM_PROMPT, MAX_ITERATIONS
from providers import get_llm_provider

load_dotenv()

app = Flask(__name__)
CORS(app)

provider = get_llm_provider()

@app.route('/')
def index():
    # Phục vụ file ui/index.html khi truy cập vào http://127.0.0.1:5000/
    ui_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ui')
    return send_from_directory(ui_dir, 'index.html')

@app.route('/api/orders', methods=['GET'])
def get_orders():
    orders = []
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'orders.csv')
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                orders.append(row)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(orders)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    query = data.get('query', '')
    mode = data.get('mode', 'baseline')
    
    if mode == 'baseline':
        response = provider.generate(query, system_prompt=CHATBOT_BASELINE_PROMPT)
        return jsonify({"mode": "baseline", "response": response})
        
    elif mode == 'react':
        scratchpad = f"Question: {query}\n"
        step = 0
        steps_log = []
        
        while step < MAX_ITERATIONS:
            step += 1
            response = provider.generate(scratchpad, system_prompt=REACT_SYSTEM_PROMPT)
            scratchpad += f"{response}\n"
            
            # Lưu lại nguyên văn output của LLM cho bước này
            steps_log.append({"type": "llm", "content": response})
            
            if "Final Answer:" in response:
                break
                
            action_match = re.search(r"Action:\s*(\w+)\[(.*?)\]", response)
            if action_match:
                tool_name = action_match.group(1).strip()
                tool_arg = action_match.group(2).strip()
                
                if (tool_arg.startswith("'") and tool_arg.endswith("'")) or (tool_arg.startswith('"') and tool_arg.endswith('"')):
                    tool_arg = tool_arg[1:-1]
                    
                if tool_name in AVAILABLE_TOOLS:
                    tool_func = AVAILABLE_TOOLS[tool_name]
                    try:
                        if "," in tool_arg:
                            args = [arg.strip(" '\"") for arg in tool_arg.split(",", 1)]
                            obs = tool_func(*args)
                        else:
                            obs = tool_func(tool_arg)
                    except Exception as e:
                        obs = f"Lỗi thực thi tool: {str(e)}"
                else:
                    obs = f"Lỗi: Không tìm thấy công cụ '{tool_name}'."
                    
                scratchpad += f"Observation: {obs}\n"
                steps_log.append({"type": "tool", "content": f"Observation: {obs}"})
                
            else:
                break
                
        return jsonify({
            "mode": "react", 
            "steps": steps_log,
            "scratchpad": scratchpad
        })

if __name__ == '__main__':
    print(f"=======================================")
    print(f"🚀 WEB API SERVER (FLASK) IS RUNNING...")
    print(f"🔌 LLM Provider đang hoạt động: {provider.__class__.__name__}")
    print(f"=======================================")
    app.run(port=5000, debug=True)
