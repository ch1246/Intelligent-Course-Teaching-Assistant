import os, sys, glob, json, time
sys.stdout.reconfigure(encoding='utf-8')
import requests

BASE_URL = 'http://localhost:9000'
# 注意: Django的URL不带尾部斜杠
LOGIN_URL = f'{BASE_URL}/api/auth/login'
COURSE_ID = 2
SLIDES_DIR = r'D:\work\code\rag\berkeley-stat-157\slides-zh'

# 1. 登录获取token
print('=== 登录 ===')
login_resp = requests.post(LOGIN_URL, json={
    'username': 'admin',
    'password': 'admin123',
})
if login_resp.status_code != 200:
    print(f'登录失败: {login_resp.status_code} {login_resp.text}')
    sys.exit(1)
token = login_resp.json()['data']['accessToken']
headers = {'Authorization': f'Bearer {token}'}
print('登录成功')

# 2. 检查/创建向量集合
print('\n=== 检查向量集合 ===')
col_resp = requests.get(f'{BASE_URL}/api/admin/vector-db/collections', headers=headers)
collections = col_resp.json()['data']['list']
target_col = None
for c in collections:
    if c.get('course') == COURSE_ID or c.get('course_id') == COURSE_ID:
        target_col = c
        break

if not target_col:
    print('未找到课程向量集合，创建中...')
    create_resp = requests.post(f'{BASE_URL}/api/admin/vector-db/collections', json={
        'name': '机器学习·知识库',
        'course': COURSE_ID,
        'embedding_model': 'bge-large-zh-v1.5',
        'dimension': 1024,
        'description': '机器学习课程知识库',
    }, headers=headers)
    if create_resp.status_code in (200, 201):
        target_col = create_resp.json()['data']
        print(f'创建成功: ID={target_col["id"]}')
    else:
        print(f'创建失败: {create_resp.status_code} {create_resp.text}')
        sys.exit(1)
else:
    print(f'找到集合: ID={target_col["id"]}, Name={target_col["name"]}')

col_id = target_col['id']

# 3. 上传PPT文件
print(f'\n=== 上传PPT文件到课程 {COURSE_ID} ===')
pptx_files = sorted(glob.glob(os.path.join(SLIDES_DIR, '*.pptx')))
print(f'找到 {len(pptx_files)} 个PPT文件')

uploaded_ids = []
for fpath in pptx_files:
    fname = os.path.basename(fpath)
    fsize = os.path.getsize(fpath)
    print(f'  上传: {fname} ({fsize/1024/1024:.1f}MB)...', end=' ')
    with open(fpath, 'rb') as f:
        resp = requests.post(f'{BASE_URL}/api/files/', files={
            'file': (fname, f, 'application/vnd.openxmlformats-officedocument.presentationml.presentation'),
        }, data={'course_id': COURSE_ID}, headers=headers)
    if resp.status_code in (200, 201):
        data = resp.json()['data']
        uploaded_ids.append(data['id'])
        print(f'OK (ID={data["id"]})')
    else:
        print(f'FAIL: {resp.status_code} {resp.text[:100]}')
    time.sleep(0.5)

print(f'\n成功上传 {len(uploaded_ids)}/{len(pptx_files)} 个文件')

# 4. 触发重新索引
print(f'\n=== 触发重新索引 (集合ID={col_id}) ===')
reindex_resp = requests.post(f'{BASE_URL}/api/admin/vector-db/collections/{col_id}/reindex', headers=headers)
if reindex_resp.status_code == 200:
    data = reindex_resp.json()['data']
    print(f'索引完成!')
    print(f'  文档数: {data.get("document_count")}')
    print(f'  分块数: {data.get("chunk_count")}')
    print(f'  向量数: {data.get("vector_count")}')
else:
    print(f'索引请求: {reindex_resp.status_code} {reindex_resp.text[:200]}')

print('\n完成!')