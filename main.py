# main.py

import functions_framework
import json
from google.cloud import storage 
import os 
import numpy as np 
from pygltflib import GLTF2, Buffer, BufferView, Accessor, Mesh, Primitive, Node, Scene, Asset
import io 

# Cloud Storage クライアントの初期化
storage_client = storage.Client()

# Cloud Storage バケット名: 環境変数から取得する形式に戻す
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "your-gcs-bucket-name-if-not-set")
if GCS_BUCKET_NAME == "your-gcs-bucket-name-if-not-set":
    print("WARNING: GCS_BUCKET_NAME environment variable is not set in Cloud Functions. Using placeholder. Please set it in Cloud Build or function configuration.")


@functions_framework.http
def model_generate_v2(request):
    """
    HTTP リクエストを受け取り、Cloud Storageから動的にファイルを読み込み、/tmpに保存し、
    その後固定の立方体GLBモデルを返すCloud Function。
    """
    # CORS プリフライトリクエストへの対応
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # レスポンスヘッダーの設定 (成功時はGLB、エラー時はJSON)
    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'model/gltf-binary' # デフォルトはGLBを想定
    }

    request_json = request.get_json(silent=True)
    received_task_id = None
    received_file_extension = None 

    if request_json:
        received_task_id = request_json.get('taskId')
        received_file_extension = request_json.get('fileExtension')
        print(f"Cloud Functions: Received JSON - taskId: {received_task_id}, fileExtension: {received_file_extension}")
    else:
        error_message = "No JSON data found in request body."
        print(f"Error: {error_message}")
        response_headers['Content-Type'] = 'application/json'
        return (json.dumps({'error': error_message}), 400, response_headers)

    if not received_task_id:
        error_message = "Missing 'taskId' in request body."
        print(f"Error: {error_message}")
        response_headers['Content-Type'] = 'application/json'
        return (json.dumps({'error': error_message}), 400, response_headers)
    
    if not received_file_extension:
        error_message = "Missing 'fileExtension' in request body."
        print(f"Error: {error_message}")
        response_headers['Content-Type'] = 'application/json'
        return (json.dumps({'error': error_message}), 400, response_headers)

    try:
        # --- GCSからのファイル読み込み (動的なパスに戻す) ---
        # Next.js API Route と同じパス形式 `uploads/UUID.EXT` で読み込む
        gcs_file_path = f"uploads/{received_task_id}.{received_file_extension}" 
        print(f"Cloud Functions: Attempting to download from GCS path: gs://{GCS_BUCKET_NAME}/{gcs_file_path}")

        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(gcs_file_path)

        if not blob.exists():
            error_message = f"File not found in GCS: gs://{GCS_BUCKET_NAME}/{gcs_file_path}. Please check filename or upload status. (Expected path: {gcs_file_path})"
            print(f"Error: {error_message}")
            response_headers['Content-Type'] = 'application/json' # エラー時はJSONで返す
            return (json.dumps({'error': error_message}), 404, response_headers) # 404 Not Foundとして返す

        file_contents = blob.download_as_bytes()
        print(f"File '{gcs_file_path}' downloaded from GCS. Size: {len(file_contents)} bytes")

        # 2. 読み込んだファイルを /tmp ディレクトリに保存 (確認のため)
        local_temp_file_path = os.path.join("/tmp", f"{received_task_id}.{received_file_extension}")
        with open(local_temp_file_path, "wb") as f:
            f.write(file_contents)
        print(f"File successfully saved to local /tmp: {local_temp_file_path}")

        # --- 固定の立方体 GLB モデルの頂点データとインデックスデータを作成 ---
        # この部分はファイルの内容に関わらず、固定のモデルを生成します。
        vertices = np.array([
            [-0.5, -0.5, -0.5], # 0
            [ 0.5, -0.5, -0.5], # 1
            [ 0.5,  0.5, -0.5], # 2
            [-0.5,  0.5, -0.5], # 3
            [-0.5, -0.5,  0.5], # 4
            [ 0.5, -0.5,  0.5], # 5
            [ 0.5,  0.5,  0.5], # 6
            [-0.5,  0.5,  0.5], # 7
        ], dtype=np.float32)

        indices = np.array([
            0, 1, 2,  0, 2, 3,  # Front face (-Z)
            1, 5, 6,  1, 6, 2,  # Right face (+X)
            5, 4, 7,  5, 7, 6,  # Back face (+Z)
            4, 0, 3,  4, 3, 7,  # Left face (-X)
            3, 2, 6,  3, 6, 7,  # Top face (+Y)
            4, 5, 1,  4, 1, 0   # Bottom face (-Y)
        ], dtype=np.uint16)

        # --- GLBファイル構造の構築 (pygltflib を使用) ---
        gltf = GLTF2()

        # 1. バッファ (実際のバイナリデータ: 頂点とインデックスを結合)
        vertex_buffer_byte_offset = 0
        vertex_buffer_bytes = vertices.tobytes()
        index_buffer_byte_offset = len(vertex_buffer_bytes)
        index_buffer_bytes = indices.tobytes()

        buffer_data = vertex_buffer_bytes + index_buffer_bytes
        buffer = Buffer(byteLength=len(buffer_data))
        gltf.buffers.append(buffer)

        # 2. バッファビュー (バッファ内のデータ範囲と用途を定義)
        buffer_view_vertices = BufferView(
            buffer=0, byteOffset=vertex_buffer_byte_offset, byteLength=len(vertex_buffer_bytes), target=34962)
        gltf.bufferViews.append(buffer_view_vertices)

        buffer_view_indices = BufferView(
            buffer=0, byteOffset=index_buffer_byte_offset, byteLength=len(index_buffer_bytes), target=34963)
        gltf.buffers.append(buffer_view_indices)

        # 3. アクセサ (バッファビュー内のデータへのアクセス方法を定義)
        accessor_vertices = Accessor(
            bufferView=0, byteOffset=0, componentType=5126, count=len(vertices), type='VEC3',
            max=vertices.max(axis=0).tolist(), min=vertices.min(axis=0).tolist())
        gltf.accessors.append(accessor_vertices)

        accessor_indices = Accessor(
            bufferView=1, byteOffset=0, componentType=5123, count=len(indices), type='SCALAR',
            max=[int(indices.max())], min=[int(indices.min())])
        gltf.accessors.append(accessor_indices)

        # 4. プリミティブ (描画するジオメトリの最小単位)
        primitive = Primitive(
            attributes={"POSITION": 0}, 
            indices=1, 
            mode=4 
        )
        mesh = Mesh(primitives=[primitive])
        gltf.meshes.append(mesh)

        # 6. ノード (メッシュのシーン内での変換・配置情報)
        node = Node(mesh=0) 
        gltf.nodes.append(node)

        # 7. シーン (ノードの集合)
        scene = Scene(nodes=[0]) 
        gltf.scenes.append(scene)

        # 8. デフォルトシーンの設定
        gltf.scene = 0

        # 9. アセット情報 (glTFファイルのメタデータ)
        gltf.asset = Asset(version="2.0", generator="pygltflib")

        # --- GLB (glTF Binary) バイナリデータを生成してHTTPレスポンスとして返す ---
        # io.BytesIOを使い、gltf.save()でメモリに書き込み、その内容を取得する
        glb_buffer = io.BytesIO()
        gltf.save(glb_buffer, binchunk=buffer_data) # save()メソッドを呼び出す
        glb_data = glb_buffer.getvalue() # 書き込んだ内容を取得

        # 成功時のレスポンス (Content-Typeはmodel/gltf-binary)
        return glb_data, 200, response_headers

    except Exception as e:
        # エラー発生時のログ出力とJSONエラーレスポンス
        error_message = f"3D Model generation or GCS access failed: {str(e)}"
        print(f"Error: {error_message}")
        response_headers['Content-Type'] = 'application/json' 
        if "File not found in GCS" in str(e):
            return (json.dumps({'error': error_message}), 404, response_headers)
        else:
            return (json.dumps({'error': error_message}), 500, response_headers)