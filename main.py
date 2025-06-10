# main.py (修正案)
import functions_framework
import json
import time # ★追加: time モジュールをインポート

# ... (中略) ...

@functions_framework.http
def model_generate_v2(request):
    # ... (中略) ...

    try:
        # ★★★ Cloud Functions からのシンプルなJSONレスポンス ★★★
        response_data = {
            "status": "success",
            "message": "Hello from Cloud Functions!",
            "received_task_id": received_task_id,
            "timestamp": time.time() # ★修正: Pythonで現在のタイムスタンプ（Unixタイムスタンプ）を取得
            # または、より人間が読める形式にするなら
            # "timestamp": str(datetime.datetime.now())
        }
        print(f"Cloud Functions: Responding with: {response_data}")
        return (json.dumps(response_data), 200, response_headers)

    except Exception as e:
        error_message = f"Cloud Functions internal error (debug mode): {str(e)}"
        print(f"Error: {error_message}")
        return (json.dumps({'error': error_message}), 500, response_headers)