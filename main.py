import functions_framework
import json
import numpy as np
from pygltflib import GLTF2, Buffer, BufferView, Accessor, Mesh, Primitive, Node, Scene, Asset

@functions_framework.http
def generate_3d_model(request):
    """
    HTTP リクエストを受け取り、簡単な3Dモデル (立方体) を生成し、GLB形式で返す。
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

    # CORS ヘッダー
    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'model/gltf-binary' # GLBファイルであることを示すMIMEタイプ
    }

    # Next.jsからのデータ取得 (今回は例として使用しないが、ここにロジックを追加)
    # request_json = request.get_json(silent=True)
    # if request_json and 'model_params' in request_json:
    #     # 例: request_json['model_params']['size'] などでモデルのサイズを制御
    #     pass

    # --- 簡単な立方体の頂点データとインデックスデータを作成 ---
    # 頂点データ (X, Y, Z)
    # 立方体の8つの頂点
    vertices = np.array([
        [-0.5, -0.5, -0.5],
        [ 0.5, -0.5, -0.5],
        [ 0.5,  0.5, -0.5],
        [-0.5,  0.5, -0.5],
        [-0.5, -0.5,  0.5],
        [ 0.5, -0.5,  0.5],
        [ 0.5,  0.5,  0.5],
        [-0.5,  0.5,  0.5],
    ], dtype=np.float32)

    # インデックスデータ (三角形の面を定義)
    # 12個の三角形 (6面 * 2三角形/面)
    indices = np.array([
        0, 1, 2,  0, 2, 3,  # Front face
        1, 5, 6,  1, 6, 2,  # Right face
        5, 4, 7,  5, 7, 6,  # Back face
        4, 0, 3,  4, 3, 7,  # Left face
        3, 2, 6,  3, 6, 7,  # Top face
        4, 5, 1,  4, 1, 0   # Bottom face
    ], dtype=np.uint16) # インデックスはuint16が一般的

    # --- GLBファイル構造の構築 ---
    gltf = GLTF2()

    # 1. バッファ (実際のバイナリデータ)
    # 頂点データとインデックスデータを結合して一つのバイナリバッファにする
    vertex_buffer_byte_offset = 0
    vertex_buffer_bytes = vertices.tobytes()
    index_buffer_byte_offset = len(vertex_buffer_bytes)
    index_buffer_bytes = indices.tobytes()

    buffer_data = vertex_buffer_bytes + index_buffer_bytes
    buffer = Buffer(byteLength=len(buffer_data))
    gltf.buffers.append(buffer)

    # 2. バッファビュー (バッファ内のデータ範囲と用途を定義)
    # 頂点データのバッファビュー
    buffer_view_vertices = BufferView(
        buffer=0,
        byteOffset=vertex_buffer_byte_offset,
        byteLength=len(vertex_buffer_bytes),
        target=34962 # ARRAY_BUFFER (頂点属性)
    )
    gltf.bufferViews.append(buffer_view_vertices)

    # インデックスデータのバッファビュー
    buffer_view_indices = BufferView(
        buffer=0,
        byteOffset=index_buffer_byte_offset,
        byteLength=len(index_buffer_bytes),
        target=34963 # ELEMENT_ARRAY_BUFFER (インデックス)
    )
    gltf.bufferViews.append(buffer_view_indices)

    # 3. アクセサ (バッファビュー内のデータへのアクセス方法を定義)
    # 頂点データのアクセサ
    accessor_vertices = Accessor(
        bufferView=0, # buffer_view_vertices を参照
        byteOffset=0,
        componentType=5126, # FLOAT (np.float32)
        count=len(vertices),
        type='VEC3', # 3成分 (X, Y, Z)
        max=vertices.max(axis=0).tolist(), # Bounding box max
        min=vertices.min(axis=0).tolist(), # Bounding box min
    )
    gltf.accessors.append(accessor_vertices)

    # インデックスデータのアクセサ
    accessor_indices = Accessor(
        bufferView=1, # buffer_view_indices を参照
        byteOffset=0,
        componentType=5123, # UNSIGNED_SHORT (np.uint16)
        count=len(indices),
        type='SCALAR', # 1成分 (インデックス値)
        max=[int(indices.max())],
        min=[int(indices.min())],
    )
    gltf.accessors.append(accessor_indices)

    # 4. プリミティブ (描画するジオメトリ)
    primitive = Primitive(
        attributes=Accessor(POSITION=0), # 頂点アクセサを参照
        indices=1, # インデックスアクセサを参照
        mode=4 # TRIANGLES
    )

    # 5. メッシュ (複数のプリミティブを含む)
    mesh = Mesh(primitives=[primitive])
    gltf.meshes.append(mesh)

    # 6. ノード (メッシュのシーン内での配置)
    node = Node(mesh=0) # mesh[0] を参照
    gltf.nodes.append(node)

    # 7. シーン (ノードの集合)
    scene = Scene(nodes=[0]) # node[0] を参照
    gltf.scenes.append(scene)

    # 8. デフォルトシーンの設定
    gltf.scene = 0

    # 9. アセット情報
    gltf.asset = Asset(version="2.0", generator="pygltflib")

    # --- GLB バイナリデータを生成して返す ---
    try:
        # GLB形式でバイトデータを書き出す
        glb_data = gltf.glb_bytes_representation(binchunk=buffer_data)

        # バイナリデータとしてHTTPレスポンスを返す
        return glb_data, 200, response_headers
    except Exception as e:
        error_message = f"Failed to generate GLB: {str(e)}"
        print(f"Error: {error_message}")
        return (json.dumps({'error': error_message}), 500, response_headers)