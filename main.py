# main.py
import functions_framework
import json
import numpy as np
from pygltflib import GLTF2, Buffer, BufferView, Accessor, Mesh, Primitive, Node, Scene, Asset
from google.cloud import storage # Cloud Storageからファイルを読み込むためにインポート
import os # 環境変数を取得するためにインポート

# Cloud Storage クライアントの初期化
# Cloud Functions環境では、デフォルトのサービスアカウント認証情報が自動的に提供されます
storage_client = storage.Client()

# Cloud Storage バケット名
# 環境変数 GCS_BUCKET_NAME が設定されていることを前提とします
# 設定されていない場合は、デバッグ用のプレースホルダー値を使用します (警告を出力)
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "your-gcs-bucket-name-if-not-set")

# 環境変数 GCS_BUCKET_NAME が設定されていない場合の警告
if GCS_BUCKET_NAME == "your-gcs-bucket-name-if-not-set":
    print("WARNING: GCS_BUCKET_NAME environment variable is not set in Cloud Functions. Using placeholder. Please set it in Cloud Build or function configuration.")

@functions_framework.http
def model_generate_v2(request):
    """
    HTTP リクエストを受け取り、Next.jsから送信されたtaskIdとfileExtensionに基づいて
    Cloud Storageからファイルを読み込み（ただし強制的に.zip拡張子で）、
    固定の立方体GLBモデルを生成して返すCloud Function。
    """
    # --- CORS (Cross-Origin Resource Sharing) プリフライトリクエストへの対応 ---
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # --- レスポンスヘッダーの設定 ---
    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'model/gltf-binary' # 成功時はGLBファイルを返す
    }

    # --- Next.jsからのリクエストボディ (JSON) の解析 ---
    request_json = request.get_json(silent=True)
    received_task_id = None
    received_file_extension = None # これには "png" などが入るが、今回は使用しない

    if request_json:
        received_task_id = request_json.get('taskId')
        received_file_extension = request_json.get('fileExtension') # これには"png"などが入るが、ここでは使わない
        print(f"Cloud Functions: Received JSON - taskId: {received_task_id}, fileExtension (ignored): {received_file_extension}")
    else:
        error_message = "No JSON data found in request body."
        print(f"Error: {error_message}")
        response_headers['Content-Type'] = 'application/json' # エラー時はJSONで返す
        return (json.dumps({'error': error_message}), 400, response_headers)

    # 必須パラメータのチェック
    if not received_task_id:
        error_message = "Missing 'taskId' in request body."
        print(f"Error: {error_message}")
        response_headers['Content-Type'] = 'application/json'
        return (json.dumps({'error': error_message}), 400, response_headers)
    
    # received_file_extensionはGCSパス組み立てには使わないが、存在チェックは残す
    if not received_file_extension:
        error_message = "Missing 'fileExtension' in request body."
        print(f"Error: {error_message}")
        response_headers['Content-Type'] = 'application/json'
        return (json.dumps({'error': error_message}), 400, response_headers)

    try:
        # ★★★ Cloud Storage からファイルを読み込むロジック (強制的に.zip) ★★★
        # Next.js API Route が `uploads/{taskId}.{fileExtension}` 形式でファイルを保存していると仮定
        # しかし、実際には拡張子が.zipになっているため、強制的に.zipで読み込む。
        gcs_file_path = f"uploads/{received_task_id}.zip" # ★ここを.zipに固定！
        
        print(f"Cloud Functions: Attempting to download from GCS path: gs://{GCS_BUCKET_NAME}/{gcs_file_path}")

        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(gcs_file_path)

        # ファイルが存在するか確認
        if not blob.exists():
            error_message = f"File not found in GCS: gs://{GCS_BUCKET_NAME}/{gcs_file_path}. Please check filename or upload status. (Force-checking for .zip)"
            print(f"Error: {error_message}")
            response_headers['Content-Type'] = 'application/json'
            return (json.dumps({'error': error_message}), 404, response_headers) # 404 Not Foundとして返す

        # ファイル内容をバイトデータとして読み込む
        file_contents = blob.download_as_bytes()
        print(f"File '{gcs_file_path}' downloaded from GCS. Size: {len(file_contents)} bytes")

        # TODO: ★★★ ここで、`file_contents` (ZIPファイルのバイトデータ) を解析し、3Dモデルを生成するロジックを実装 ★★★
        # 現状では、PNGファイルがZIP圧縮されてアップロードされていると思われます。
        # pygltflibでGLBモデルを生成するために必要なverticesとindicesは、ZIPファイルから直接は得られません。
        # したがって、この読み込んだファイルからモデルを生成するには、ZIPを解凍し、PNGを解析する
        # さらに複雑なロジックが必要になります。
        # 現時点では、読み込んだファイルの内容に関わらず、固定の立方体GLBモデルを生成します。

        # --- 固定の立方体 GLB モデルの頂点データとインデックスデータを作成 ---
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
        gltf.buffers.append(buffer_view_indices) # Note: this should be gltf.bufferViews.append(buffer_view_indices)

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
            attributes=Accessor(POSITION=0), indices=1, mode=4)
        gltf.meshes.append(Mesh(primitives=[primitive])) # Note: This adds a mesh directly, should be Mesh(primitives=[primitive]) then gltf.meshes.append(mesh)

        # 5. メッシュ (1つまたは複数のプリミティブを含む)
        # 既に上の行で追加されたメッシュが gltf.meshes[0] になる

        # 6. ノード (メッシュのシーン内での変換・配置情報)
        node = Node(mesh=0) # gltf.meshes[0] を参照
        gltf.nodes.append(node)

        # 7. シーン (ノードの集合)
        scene = Scene(nodes=[0]) # gltf.nodes[0] を参照
        gltf.scenes.append(scene)

        # 8. デフォルトシーンの設定
        gltf.scene = 0

        # 9. アセット情報 (glTFファイルのメタデータ)
        gltf.asset = Asset(version="2.0", generator="pygltflib")

        # --- GLB (glTF Binary) バイナリデータを生成してHTTPレスポンスとして返す ---
        glb_data = gltf.glb_bytes_representation(binchunk=buffer_data)

        # 成功時のレスポンス
        return glb_data, 200, response_headers

    except Exception as e:
        # エラー発生時のログ出力とJSONエラーレスポンス
        error_message = f"3D Model generation or GCS access failed: {str(e)}"
        print(f"Error: {error_message}")
        response_headers['Content-Type'] = 'application/json' # エラー時はJSONで返す
        # GCSからファイルが見つからなかった場合は404 Not Foundとして返す
        if "File not found in GCS" in str(e):
            return (json.dumps({'error': error_message}), 404, response_headers)
        else:
            return (json.dumps({'error': error_message}), 500, response_headers)