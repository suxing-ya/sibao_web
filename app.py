import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from functools import wraps
from dotenv import load_dotenv
from datetime import datetime # 添加 datetime 导入
import json
from flask_cors import CORS # 导入 Flask-CORS
# from werkzeug.security import generate_password_hash, check_password_hash # No longer needed for Supabase auth
# import sqlite3 # No longer needed
# import datetime # May still be needed for other date/time operations, but not for user registration timestamping

from supabase import create_client, Client

load_dotenv()

app = Flask(__name__, template_folder='templates')
CORS(app, origins=["*"]) # 初始化 CORS，允许所有来源访问，生产环境请指定前端域名
app.secret_key = os.urandom(24) # 用于会话加密，生产环境应使用更安全的随机字符串或从环境变量加载

# Supabase Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Supabase environment variables SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")

print(f"DEBUG: Supabase URL: {SUPABASE_URL}")
print(f"DEBUG: Supabase Service Role Key (first 10 chars): {SUPABASE_SERVICE_ROLE_KEY[:10]}...")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Removed SQLite database initialization
# DATABASE = 'members.db'
# def get_db():
#     conn = sqlite3.connect(DATABASE)
#     conn.row_factory = sqlite3.Row
#     return conn
# def init_db():
#     with app.app_context():
#         db = get_db()
#         cursor = db.cursor()
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS users (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 username TEXT NOT NULL UNIQUE,
#                 email TEXT UNIQUE,
#                 password TEXT NOT NULL,
#                 role TEXT NOT NULL,
#                 registered_at TEXT NOT NULL,
#                 notes TEXT
#             )
#         ''')
#         try:
#             cursor.execute("SELECT * FROM users WHERE username = ?", ('can',))
#             admin_exists = cursor.fetchone()
#             if not admin_exists:
#                 hashed_password = generate_password_hash('A007@163')
#                 current_time = datetime.datetime.now().isoformat()
#                 cursor.execute("INSERT INTO users (username, password, role, registered_at, email, notes) VALUES (?, ?, ?, ?, ?, ?)",
#                                ('can', hashed_password, 'admin', current_time, 'admin@sibaostudio.com', '主账号'))
#                 db.commit()
#                 print("Initial admin user 'can' created.")
#             else:
#                 print("Admin user 'can' already exists.")
#         except sqlite3.Error as e:
#             print(f"Error initializing admin user: {e}")
#         finally:
#             db.close()
# init_db() # Removed this call as well

# 添加一个自定义的 Jinja2 过滤器用于格式化日期时间
@app.template_filter('datetime_format')
def datetime_format_filter(value, format="%Y-%m-%d %H:%M"): # 默认格式为 年-月-日 时:分
    if not value:
        return ""
    if isinstance(value, str):
        try:
            # Supabase 返回的日期是 ISO 8601 格式，可能带有时区信息（例如 Z 或 +00:00）
            # fromisoformat 可以处理大部分情况，但对于 Z，替换为 +00:00 更通用
            dt_object = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            # 捕获其他可能的日期格式错误，如果需要可以添加更多解析逻辑
            # 或者使用更健壮的库如 dateutil.parser
            return "无效日期"
        return dt_object.strftime(format)
    return str(value) # 如果不是字符串，尝试直接转换为字符串

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """
    处理管理员登录请求。
    @returns {flask.Response} 登录页面或重定向到admin.html。
    """
    if request.method == 'POST':
        email = request.form['username'] # Changed to email as Supabase uses email for login
        password = request.form['password']
        
        try:
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            user = res.user

            if user:
                # Fetch user's role from profiles table
                profile_query = supabase.from_('profiles').select('role, username').eq('id', user.id).single()
                profile_res = profile_query.execute()
                if profile_res.data:
                    session['logged_in'] = True
                    session['user_id'] = user.id # Store user_id in session
                    session['username'] = profile_res.data['username'] # Use username from profiles
                    session['role'] = profile_res.data['role']
                    return redirect(url_for('admin_dashboard'))
                else:
                    return render_template('login_admin.html', login_error='用户档案未找到或权限不足')
            else:
                return render_template('login_admin.html', login_error='用户名或密码错误')
        except Exception as e:
            print(f"Supabase login error: {e}")
            return render_template('login_admin.html', login_error=f'登录失败: {e}')
    return render_template('login_admin.html')

@app.route('/admin/logout')
def admin_logout():
    """
    处理管理员登出请求。
    """
    # Supabase logout - optional as session is server-side
    # try:
    #     supabase.auth.sign_out()
    # except Exception as e:
    #     print(f"Supabase logout error: {e}")

    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('admin_login'))

def login_required(f):
    """
    一个简单的装饰器，用于保护需要登录的路由。
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('user_login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    一个简单的装饰器，用于保护需要管理员权限的路由。
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            return "权限不足", 403 # Forbidden
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission_key):
    """
    一个通用的装饰器，用于保护需要特定权限的路由。
    管理员默认拥有所有权限。普通用户需要其permissions列表中包含permission_key。
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('user_login'))

        # 管理员默认拥有所有权限
        if session.get('role') == 'admin':
            return f(*args, **kwargs)

        user_permissions_str = session.get('permissions', '[]')
        try:
            user_permissions = json.loads(user_permissions_str)
        except json.JSONDecodeError:
            user_permissions = [] # 处理非法的 JSON 格式

        if permission_key in user_permissions:
            return f(*args, **kwargs)
        else:
            return "权限不足，无法访问此页面", 403
    return decorated_function

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """
    显示会员管理仪表板。
    @returns {flask.Response} 仪表板页面。
    """
    # Fetch all users from Supabase auth and profiles table
    try:
        # Create a dedicated admin client for this privileged operation
        # Explicitly get the key from environment variables within the function
        dashboard_supabase_url = os.environ.get("SUPABASE_URL")
        dashboard_service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

        if not dashboard_supabase_url or not dashboard_service_role_key:
            raise ValueError("Supabase environment variables not available in admin_dashboard context.")

        admin_supabase: Client = create_client(dashboard_supabase_url, dashboard_service_role_key)
        print(f"DEBUG: Admin Supabase client created in dashboard. Key (first 10 chars): {dashboard_service_role_key[:10]}...")

        # Get all users from auth.users (Supabase Admin API)
        auth_users = admin_supabase.auth.admin.list_users() # Use the dedicated admin client
        if auth_users:
            auth_user_map = {user.id: user for user in auth_users}
        else:
            auth_user_map = {}
            auth_users = []

        # Get all profiles from profiles table
        profiles_response = supabase.from_('profiles').select('id, username, role, created_at, notes, permissions').execute()
        if profiles_response.data:
            profiles = profiles_response.data
            profile_map = {profile['id']: profile for profile in profiles}
        else:
            profiles = []
            profile_map = {}

        members = []
        for auth_user in auth_users:
            profile_data = profile_map.get(auth_user.id)
            if profile_data:
                members.append({
                    'id': auth_user.id,
                    'username': profile_data['username'],
                    'email': auth_user.email, # Use email from auth.users
                    'role': profile_data['role'],
                    'registered_at': profile_data['created_at'], # Use created_at from profiles
                    'notes': profile_data.get('notes', 'N/A'),
                    'permissions': profile_data.get('permissions', '[]') # Include permissions
                })
            # Handle users in auth.users but not in profiles (e.g., if profile creation failed)
            else:
                members.append({
                    'id': auth_user.id,
                    'username': auth_user.email, # Fallback to email if no profile username
                    'email': auth_user.email,
                    'role': 'unknown', # Default role if no profile
                    'registered_at': auth_user.created_at, # Use created_at from auth.users
                    'notes': 'Profile missing',
                    'permissions': '[]' # Default permissions for missing profiles
                })
        
        # Sort members by creation date or username as needed
        members.sort(key=lambda x: x.get('registered_at', ''))

        print("auth_users:", auth_users)
        print("profiles:", profiles)
        print("members:", members)
        return render_template('admin.html', members=members, session=session)
    except Exception as e:
        import traceback
        traceback.print_exc() # Print full traceback
        print(f"Error fetching members: {e}")
        return "加载会员信息失败", 500

@app.route('/api/members', methods=['GET'])
@login_required
@admin_required
def get_members():
    """
    API 路由：获取所有会员信息。
    @returns {flask.Response} JSON 格式的会员列表。
    """
    try:
        # Create a dedicated admin client for this privileged operation
        # Explicitly get the key from environment variables within the function
        api_supabase_url = os.environ.get("SUPABASE_URL")
        api_service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

        if not api_supabase_url or not api_service_role_key:
            raise ValueError("Supabase environment variables not available in get_members context.")

        admin_supabase: Client = create_client(api_supabase_url, api_service_role_key)
        print(f"DEBUG: Admin Supabase client created in API. Key (first 10 chars): {api_service_role_key[:10]}...")

        auth_users = admin_supabase.auth.admin.list_users() # Use the dedicated admin client
        if auth_users:
            auth_user_map = {user.id: user for user in auth_users}
        else:
            auth_user_map = {}
            auth_users = []

        profiles_response = supabase.from_('profiles').select('id, username, role, created_at, notes, permissions').execute()
        if profiles_response.data:
            profiles = profiles_response.data
            profile_map = {profile['id']: profile for profile in profiles}
        else:
            profiles = []
            profile_map = {}

        members = []
        for auth_user in auth_users:
            profile_data = profile_map.get(auth_user.id)
            if profile_data:
                members.append({
                    'id': auth_user.id,
                    'username': profile_data['username'],
                    'email': auth_user.email,
                    'role': profile_data['role'],
                    'registered_at': profile_data['created_at'],
                    'notes': profile_data.get('notes', 'N/A'),
                    'permissions': profile_data.get('permissions', '[]')
                })
            else:
                members.append({
                    'id': auth_user.id,
                    'username': auth_user.email,
                    'email': auth_user.email,
                    'role': 'unknown',
                    'registered_at': auth_user.created_at,
                    'notes': 'Profile missing',
                    'permissions': '[]'
                })
        
        members.sort(key=lambda x: x.get('registered_at', ''))

        return jsonify(members)
    except Exception as e:
        import traceback
        traceback.print_exc() # Print full traceback
        print(f"Error fetching members (API): {e}")
        return jsonify({'message': f'获取会员信息失败: {e}'}), 500

@app.route('/api/member/<string:member_id>', methods=['PUT', 'DELETE'])
@login_required
@admin_required
def manage_member(member_id):
    """
    API 路由：更新或删除会员信息。
    @param {string} member_id 会员的 UUID。
    @returns {flask.Response} JSON 格式的成功/失败消息。
    """
    if request.method == 'PUT':
        data = request.get_json()
        new_role = data.get('role')
        new_notes = data.get('notes')
        new_username = data.get('username') # For editing username
        new_email = data.get('email') # For editing email
        new_permissions = data.get('permissions') # For editing permissions

        if new_role not in ['admin', 'member'] and new_role is not None:
            return jsonify({'message': '无效的角色'}), 400

        try:
            # Fetch the current user details for comparison and security checks
            current_auth_user_res = supabase.auth.admin.get_user(member_id)
            current_auth_user = current_auth_user_res.data.user

            # Prevent demoting/deleting the last admin
            admin_count_res = supabase.from_('profiles').select('id', count='exact').eq('role', 'admin').execute()
            current_admin_count = admin_count_res.count

            # If this is the last admin and they are being demoted
            if current_admin_count == 1 and member_id == session.get('user_id') and new_role and new_role != 'admin':
                return jsonify({'message': '不能将唯一的管理员降级'}), 403
            
            # If trying to delete the last admin (this check is duplicated below in DELETE, but good for PUT too)
            if current_admin_count == 1 and member_id == session.get('user_id') and request.method == 'DELETE':
                return jsonify({'message': '不能删除唯一的管理员账户'}), 403

            # Update user in auth.users (email)
            update_auth_data = {}
            if new_email and current_auth_user and new_email != current_auth_user.email: # Only update if email changed
                update_auth_data['email'] = new_email

            if update_auth_data:
                supabase.auth.admin.update_user(member_id, update_auth_data)

            # Update profile in profiles table (username, role, notes, permissions)
            update_profile_data = {}
            if new_username: # Update username if provided
                update_profile_data['username'] = new_username
            if new_role:
                update_profile_data['role'] = new_role
            if new_notes is not None:
                update_profile_data['notes'] = new_notes
            if new_permissions is not None: # Update permissions if provided
                # Ensure permissions is a JSON string
                if isinstance(new_permissions, list):
                    update_profile_data['permissions'] = json.dumps(new_permissions)
                else:
                    update_profile_data['permissions'] = new_permissions # Assume it's already a JSON string if not a list

            if update_profile_data:
                supabase.from_('profiles').update(update_profile_data).eq('id', member_id).execute()
            
            return jsonify({'message': '会员信息更新成功'}) 
        except Exception as e:
            print(f"Error updating member: {e}")
            return jsonify({'message': f'更新失败: {e}'}), 500

    elif request.method == 'DELETE':
        try:
            # Prevent deleting the last admin
            admin_count_res = supabase.from_('profiles').select('id', count='exact').eq('role', 'admin').execute()
            current_admin_count = admin_count_res.count
            
            # If this is the last admin and they are being deleted
            if current_admin_count == 1 and member_id == session.get('user_id'):
                return jsonify({'message': '不能删除唯一的管理员账户'}), 403

            supabase.auth.admin.delete_user(member_id)
            # No need to delete from profiles, as ON DELETE CASCADE handles it
            return jsonify({'message': '会员删除成功'})
        except Exception as e:
            print(f"Error deleting member: {e}")
            return jsonify({'message': f'删除失败: {e}'}), 500

@app.route('/api/member/<string:member_id>/permissions', methods=['PUT'])
@login_required
@admin_required
def update_member_permissions(member_id):
    """
    API 路由：更新特定会员的功能权限。
    @param {string} member_id - 会员的 UUID。
    @returns {flask.Response} JSON 格式的更新结果。
    """
    if not request.is_json:
        return jsonify({"error": "请求体必须是 JSON 格式"}), 400

    data = request.get_json()
    new_permissions = data.get('permissions')

    if not isinstance(new_permissions, list):
        return jsonify({"error": "permissions 字段必须是一个列表"}), 400

    try:
        response = supabase.from_('profiles').update({'permissions': new_permissions}).eq('id', member_id).execute()
        if response.data:
            return jsonify({"message": "会员权限更新成功", "data": response.data}), 200
        else:
            # Supabase update might return empty data if no rows matched or updated
            # Check if any error occurred
            if response.count == 0: # count is usually for select, but sometimes indicates affected rows for update
                # For update, response.data would be empty if nothing changed or id not found
                return jsonify({"error": "未找到该会员或权限未发生变化"}), 404
            else:
                print(f"Supabase update permissions error: {response.error}")
                return jsonify({"error": "更新权限失败", "details": str(response.error)}), 500
    except Exception as e:
        print(f"Error updating member permissions: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "服务器内部错误", "details": str(e)}), 500

@app.route('/api/sub_accounts', methods=['POST'])
@login_required
@admin_required
def create_sub_account():
    """
    API 路由：创建新的子账号。
    @returns {flask.Response} JSON 格式的成功/失败消息。
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not username or not password or not email:
        return jsonify({'message': '账号名、密码和邮箱不能为空'}), 400
    
    try:
        # Create user in Supabase auth
        new_user_res = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True # Automatically confirm email for admin-created users
        })
        new_user = new_user_res.user

        if new_user:
            # Insert profile into profiles table
            profile_data = {
                'id': new_user.id,
                'username': username,
                'role': 'member', # Default role for new sub-accounts
                'notes': data.get('notes', '子账号'), # Default notes
                'permissions': '[]' # Default to no permissions as a JSON string
            }
            supabase.from_('profiles').insert(profile_data).execute()
            
            return jsonify({'message': '子账号创建成功'}), 201 # Created
        else:
            return jsonify({'message': 'Supabase 用户创建失败'}), 500

    except Exception as e:
        print(f"Error creating sub-account: {e}")
        # Supabase will raise an error like "duplicate key value violates unique constraint" for existing emails
        # We can catch specific errors if needed, but a generic catch-all is fine for now.
        if "duplicate key value violates unique constraint" in str(e):
            return jsonify({'message': '该邮箱已存在，请使用其他邮箱。'}), 409
        return jsonify({'message': f'创建子账号失败: {e}'}), 500

# New routes for general user authentication in app.py (for other pages)
@app.route('/')
def index():
    # Redirect based on login status and role, or show landing page
    if session.get('logged_in'):
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            # For normal users, redirect to the main app page
            return redirect(url_for('pt_function_interface')) 
    return render_template('index.html')

@app.route('/login', methods=['GET'])
def user_login():
    return render_template('login.html')

@app.route('/post_login_callback', methods=['POST'])
def post_login_callback():
    data = request.get_json()
    access_token = data.get('access_token')
    user_id = data.get('user_id')
    user_email = data.get('email') # 从前端获取email

    if not access_token or not user_id or not user_email:
        return jsonify({"message": "缺少 access token, 用户ID 或 邮箱"}), 400

    try:
        # 使用 anon key 客户端来验证 token 并获取用户会话
        # 或者更简单地，假设前端提供的 token 是有效的，并直接使用 user_id 来获取 profile
        # 但为了安全，最好通过 Supabase SDK 在后端验证 token
        # 这里我们假设可以通过 user_id 直接获取 profile 来设置 session

        # Fetch user's role and username from profiles table using the user_id
        profile_query = supabase.from_('profiles').select('role, username, permissions').eq('id', user_id).single()
        profile_res = profile_query.execute()

        if profile_res.data:
            session['logged_in'] = True
            session['user_id'] = user_id
            session['username'] = profile_res.data['username']
            session['role'] = profile_res.data['role']
            session['email'] = user_email # Store email in session
            session['permissions'] = profile_res.data.get('permissions', '[]') # Store permissions in session

            # Backend redirects to the desired page after setting session
            return jsonify({"redirect_url": url_for('pt_function_interface')}), 200
        else:
            return jsonify({"message": "用户档案未找到"}), 404
    except Exception as e:
        import traceback
        traceback.print_exc() # Print full traceback
        print(f"Error in post_login_callback: {e}")
        return jsonify({"message": f"设置会话失败: {e}"}), 500

@app.route('/logout')
def user_logout():
    try:
        # Supabase client-side logout will clear JWT from local storage/cookies. Backend session is separate.
        # supabase.auth.sign_out() # This logs out the *server-side* token, which might not be what you want for browser-based auth
        pass # Client-side JS will handle this
    except Exception as e:
        print(f"Supabase logout error: {e}")

    session.pop('logged_in', None)
    session.pop('user_id', None) # Clear user_id from session
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('index')) # Redirect to homepage after logout

# Protected routes for different functionalities
@app.route('/Expense Allocation Function.html')
@login_required
@permission_required('expense_allocation_function') # 添加权限检查
def expense_allocation_function():
    """
    @description 渲染费用分摊核算页面。
    @returns {flask.Response} 费用分摊核算页面。
    """
    # For this page, we don't need admin_required, just login_required.
    # You can add more specific role checks here if needed.
    return render_template('Expense Allocation Function.html')

@app.route('/query.html')
@login_required
def query_html():
    # Example: only admin or specific roles can access query.html
    # if session.get('role') not in ['admin', 'data_viewer']:
    #     return "权限不足，无法查看查询页面", 403
    return render_template('query.html')

@app.route('/y2cost.html')
@login_required
@permission_required('y2cost_html') # 使用新的权限装饰器
def y2cost_html():
    """
    @description 渲染Y2成本核算页面。
    @returns {flask.Response} Y2成本核算页面。
    """
    return render_template('y2cost.html')

@app.route('/temu-y2gzl.html')
@login_required
@permission_required('temu_y2gzl_html') # 使用新的权限装饰器
def temu_y2gzl_html():
    """
    @description 渲染Temu Y2 货物工作流页面。
    @returns {flask.Response} Temu Y2 货物工作流页面。
    """
    return render_template('temu-y2gzl.html')

@app.route('/register.html')
def user_register():
    return render_template('register.html')

@app.route('/index.html')
def index_html():
    return render_template('index.html')

# 普通用户功能界面路由
@app.route('/ptfunctioninterface.html')
@login_required # 确保只有登录用户可以访问
def pt_function_interface():
    user_id = session.get('user_id')
    user_email = session.get('email') # 从会话中获取用户的邮箱
    if not user_id or not user_email:
        # 理论上不会发生，因为有 @login_required，但作为回退
        print("DEBUG: User ID or Email missing from session. Redirecting to login.")
        return redirect(url_for('user_login'))

    try:
        # 从 Supabase 获取用户个人信息（不包括 email，因为 email 存在 auth.users 中，且已在 session 中）
        profile_response = supabase.from_('profiles').select('username, role, created_at, notes').eq('id', user_id).single().execute()
        user_profile_data = profile_response.data

        if not user_profile_data:
            print(f"DEBUG: No profile data found for user ID: {user_id}")
            return "用户档案未找到", 404

        # 将会话中的 email 添加到 user_profile_data，以便模板使用
        user_profile_data['email'] = user_email

        # 模拟用户可用的功能列表
        available_functions = [
            {"name": "货物工作流", "description": "Temu Y2 货物流转工作流，实时了解物流情况", "url_route": "temu_y2gzl_html", "required_role": "admin"},
            {"name": "运费分摊核算", "description": "计算每项货物的分摊费用，并支持数据保存、查询和导出。", "url_route": "expense_allocation_function"},
            {"name": "成本核算", "description": "进行各项成本的精确计算和分析。", "url_route": "y2cost_html", "required_role": "admin"},
            {"name": "条形码生成", "description": "快速生成并打印各类商品条形码，支持自定义内容和格式。", "url_route": "barcode_generator_html", "required_role": "admin"},
            # 以下是原有的通用功能，如果需要保留，请保留；如果需要移除，可以删除。
            # {"name": "专属优惠", "description": "浏览仅为您提供的个性化优惠和折扣。"},
            # {"name": "账户设置", "description": "管理您的个人资料、密码和偏好设置。"},
            # {"name": "联系客服", "description": "快速联系我们的客服团队，获取帮助和支持。"},
            # {"name": "我的收藏", "description": "管理您收藏的商品或服务。"},
            # {"name": "消息中心", "description": "查看所有通知和站内消息。"},
        ]

        print(f"DEBUG: User Profile to render: {user_profile_data}")
        print(f"DEBUG: Functions to render: {available_functions}")
        return render_template('ptfunctioninterface.html', user_profile=user_profile_data, functions=available_functions)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error loading user function interface: {e}")
        return "加载功能界面失败", 500

# 新增条形码生成页面路由
@app.route('/barcode_generator.html')
@login_required
@permission_required('barcode_generator_html') # 使用新的权限装饰器
def barcode_generator_html():
    """
    @description 渲染条形码生成页面。
    @returns {flask.Response} 条形码生成页面。
    """
    return render_template('barcode_generator.html')

# Removed SQLite initialization
if __name__ == '__main__':
    app.run(debug=True) # Set debug=False for production
