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

# print("DEBUG: app.py started execution.") # New debug print - REMOVED FOR PRODUCTION

load_dotenv()

app = Flask(__name__, template_folder='templates')
CORS(app, origins=["*"]) # 初始化 CORS，允许所有来源访问，生产环境请指定前端域名

# Flask Secret Key for session management. MUST be a strong, fixed secret in production.
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY environment variable must be set for session security.")

# Supabase Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Supabase environment variables SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")

# print(f"DEBUG: Supabase URL: {SUPABASE_URL}") # REMOVED FOR PRODUCTION
# print(f"DEBUG: Supabase Service Role Key (first 10 chars): {SUPABASE_SERVICE_ROLE_KEY[:10]}...") # REMOVED FOR PRODUCTION

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
except Exception as e:
    import traceback
    traceback.print_exc()
    # 打印到stderr，确保gunicorn捕获
    import sys
    print(f"FATAL ERROR (PID {os.getpid()}): Supabase client initialization failed: {e}", file=sys.stderr)
    sys.stderr.flush() # Explicitly flush
    # 不再立即退出，让gunicorn处理worker的失败
    # exit(1) # Removed this line

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
                    session['email'] = email # Store email in session
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
    return redirect(url_for('index'))

def login_required(f):
    """
    一个简单的装饰器，用于保护需要登录的路由。
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            if request.is_json:
                return jsonify({"message": "未登录或会话已过期，请重新登录。"}), 401
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
            if request.is_json:
                return jsonify({"message": "权限不足，无权访问此功能。"}), 403
            return "权限不足", 403 # Forbidden for non-API requests
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission_key):
    """
    一个通用的装饰器，用于保护需要特定权限的路由。
    管理员默认拥有所有权限。普通用户需要其permissions列表中包含permission_key。
    """
    def decorator(f):
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
    return decorator

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
        # Fetch user's role and username from profiles table using the user_id
        profile_query = supabase.from_('profiles').select('role, username, permissions').eq('id', user_id).limit(1)
        profile_res = profile_query.execute()

        user_profile_data = None
        if profile_res.data and len(profile_res.data) > 0:
            user_profile_data = profile_res.data[0]

        if not user_profile_data:
            # If profile does not exist, create a new one
            print(f"DEBUG: No profile found for user_id {user_id}. Creating new profile.")
            new_profile = {
                'id': user_id,
                'username': user_email.split('@')[0], # Default username from email
                'role': 'normal', # Default role
                'created_at': datetime.now().isoformat(),
                'notes': '',
                'permissions': '[]'
            }
            insert_res = supabase.from_('profiles').insert([new_profile]).execute()
            # If execute() completes without error, it means the insert was successful.
            # The outer try-except handles any API-level errors.
            user_profile_data = insert_res.data[0] # Use the newly created profile data

        # Continue with session setup using user_profile_data (whether fetched or newly created)
        session['logged_in'] = True
        session['user_id'] = user_id
        session['username'] = user_profile_data['username'] # Use username from profile
        session['role'] = user_profile_data['role']
        session['email'] = user_email # Store email in session
        session['permissions'] = user_profile_data.get('permissions', '[]') # Store permissions in session

        # Backend redirects to the desired page after setting session
        return jsonify({"redirect_url": url_for('pt_function_interface')}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Supabase post_login_callback error: {e}")
        return jsonify({"message": f"登录失败: {e}"}), 500

@app.route('/logout', methods=['GET', 'POST'])
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
    return jsonify({"redirect_url": url_for('index')}), 200 # Redirect to homepage after logout

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
    user_profile = None

    if user_id:
        try:
            profile_query = supabase.from_('profiles').select('username, role, created_at, notes, permissions').eq('id', user_id).single()
            profile_res = profile_query.execute()
            if profile_res.data:
                user_profile = profile_res.data
                # Add email from session to user_profile for template display
                user_profile['email'] = session.get('email', 'N/A')
                # Convert permissions from JSON string to list if it exists
                if isinstance(user_profile.get('permissions'), str):
                    try:
                        user_profile['permissions'] = json.loads(user_profile['permissions'])
                    except json.JSONDecodeError:
                        user_profile['permissions'] = [] # Handle invalid JSON
                elif user_profile.get('permissions') is None:
                    user_profile['permissions'] = [] # Ensure it's a list if null
            else:
                # If user profile not found, clear session and redirect to login
                session.pop('logged_in', None)
                session.pop('username', None)
                session.pop('role', None)
                session.pop('user_id', None)
                session.pop('permissions', None) # Clear permissions as well
                return redirect(url_for('user_login'))
        except Exception as e:
            print(f"Error fetching user profile from Supabase: {e}")
            # Log the full traceback for more details
            import traceback
            traceback.print_exc()
            session.pop('logged_in', None) # Clear session on error
            session.pop('user_id', None)
            session.pop('username', None)
            session.pop('role', None)
            session.pop('permissions', None)
            return redirect(url_for('user_login')) # Redirect to login on error
    else:
        # If user_id is not in session, redirect to login
        return redirect(url_for('user_login'))
    
    # Define the functions available to users
    # Each function has a name, description, the url_route it maps to,
    # and the required permission key (matching permissions in the profiles table).
    functions = [
        {
            'name': '货物工作流',
            'description': 'Temu V2 货物包装工作流，实时了解物流情况',
            'url_route': 'temu_y2gzl_html',
            'required_permission': 'temu_y2gzl_html'
        },
        {
            'name': '运费分摊核算',
            'description': '计算每批货物的分摊费用，并支持数据保存、查询和导出。',
            'url_route': 'expense_allocation_function',
            'required_permission': 'expense_allocation_function'
        },
        {
            'name': '成本核算',
            'description': '进行各项成本数据统计和分析。',
            'url_route': 'y2cost_html',
            'required_permission': 'y2cost_html'
        },
        {
            'name': '条形码生成',
            'description': '快速生成并打印各类条形码，支持自定义内容。',
            'url_route': 'barcode_generator_html',
            'required_permission': 'barcode_generator_html'
        },
        {
            'name': '统计功能',
            'description': '查看各项业务数据统计概览。',
            'url_route': 'statistical_table_html',
            'required_permission': 'statistical_function' # 与 admin.html 中设置的权限标识符一致
        }
    ]
    
    # Pass the full functions list to the template; template handles permissions for display
    print(f"DEBUG: user_profile for template: {user_profile}")
    print(f"DEBUG: functions list sent to template: {functions}")

    return render_template('ptfunctioninterface.html', user_profile=user_profile, functions=functions)

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
                    'permissions': json.dumps(profile_data.get('permissions', [])) # 确保权限是有效的JSON字符串
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
                    'permissions': json.dumps([]) # Default permissions for missing profiles
                })

        return render_template('admin.html', members=members, session=session)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return "加载会员数据失败", 500

@app.route('/api/member/<string:member_id>/permissions', methods=['PUT'])
@login_required
@admin_required
def update_member_permissions(member_id):
    """
    更新指定会员的权限。
    @param {string} member_id - 要更新权限的会员ID。
    @returns {flask.Response} JSON 响应，指示更新成功或失败。
    """
    data = request.get_json()
    new_permissions = data.get('permissions')

    if not isinstance(new_permissions, list):
        return jsonify({"message": "请求体中缺少有效的 'permissions' 列表。"}), 400

    try:
        # Supabase update for the profiles table
        response = supabase.from_('profiles').update({'permissions': json.dumps(new_permissions)}).eq('id', member_id).execute()

        if response.data:
            return jsonify({"message": "会员权限已成功更新。"}), 200
        else:
            return jsonify({"message": "未能更新会员权限，可能会员不存在或权限已是最新。"}), 404
    except Exception as e:
        print(f"更新会员权限时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": f"服务器错误：无法更新会员权限。详情：{e}"}), 500

@app.route('/api/member/<string:member_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_member(member_id):
    """
    删除指定会员及其在 Supabase 中的关联数据。
    @param {string} member_id - 要删除的会员ID。
    @returns {flask.Response} JSON 响应，指示删除成功或失败。
    """
    try:
        # 1. 删除 profiles 表中的用户档案
        profile_delete_response = supabase.from_('profiles').delete().eq('id', member_id).execute()
        if not profile_delete_response.data:
            print(f"DEBUG: No profile found for deletion with ID {member_id} or no rows affected.")

        # 2. 删除 auth.users 中的用户 (需要Service Role Key权限)
        # 再次初始化admin_supabase客户端，确保使用正确的key
        admin_supabase_url = os.environ.get("SUPABASE_URL")
        admin_service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        admin_supabase: Client = create_client(admin_supabase_url, admin_service_role_key)

        delete_auth_user_response = admin_supabase.auth.admin.delete_user(member_id)
        # Supabase delete_user() doesn't return data directly for success, but raises exception on failure.

        return jsonify({"message": "会员及相关数据已成功删除。"}), 200
    except Exception as e:
        print(f"删除会员时发生错误: {e}")
        import traceback
        traceback.print_exc()
        # 如果是 Supabase 错误，尝试提取更具体的错误信息
        error_message = str(e)
        if hasattr(e, '__dict__') and 'json' in e.__dict__:
            try:
                error_json = json.loads(e.json)
                error_message = error_json.get('msg', error_message) # Supabase auth errors often have 'msg'
            except (json.JSONDecodeError, TypeError):
                pass # Ignore if json is not valid
        return jsonify({"message": f"服务器错误：无法删除会员。详情：{error_message}"}), 500

@app.route('/statisticaltable.html')
@login_required
@permission_required('statistical_function') # 修改权限标识符以保持一致性
def statistical_table_html():
    return render_template('statisticaltable.html')

@app.route('/api/shipping_costs/update', methods=['PUT'])
@login_required
@permission_required('statistical_table_html') # 假设统计功能页面的用户有权限修改数据
def update_shipping_cost():
    data = request.get_json()
    item_id = data.get('id')
    merchant_name_to_update = data.get('merchant_name')
    new_tax_unit_price = data.get('tax_unit_price')
    new_operating_fee = data.get('operating_fee')
    new_total_overall = data.get('total_overall') # This is the merchant-specific total overall

    if not all([item_id, merchant_name_to_update, new_tax_unit_price is not None, new_operating_fee is not None, new_total_overall is not None]):
        return jsonify({"message": "缺少必要的更新参数 (ID, 商家名称, 报税价, 操作费, 合计)"}), 400

    try:
        # 1. Fetch the existing record
        response = supabase.from_('shipping_costs').select('merchants').eq('id', item_id).single().execute()
        
        if response.data:
            existing_merchants = response.data.get('merchants', [])
            updated_merchants = []
            merchant_found = False

            for merchant_obj in existing_merchants:
                if merchant_obj.get('name') == merchant_name_to_update:
                    # Found the merchant, update its fields
                    merchant_obj['tax_unit_price'] = new_tax_unit_price
                    merchant_obj['operating_fee'] = new_operating_fee
                    merchant_obj['total_overall'] = new_total_overall # Update merchant-specific total_overall
                    merchant_found = True
                updated_merchants.append(merchant_obj)

            if not merchant_found:
                return jsonify({"message": f"未找到匹配的商家: {merchant_name_to_update}"}), 404

            # 2. Update the 'merchants' JSONB array in the database
            update_response = supabase.from_('shipping_costs').update({'merchants': updated_merchants}).eq('id', item_id).execute()

            # 即使 update_response.count 为 0，只要没有发生错误，也认为是成功，因为目标状态已达到
            if update_response.count is not None and update_response.count > 0:
                return jsonify({"message": "记录更新成功！"}), 200
            else:
                return jsonify({"message": "记录未发生变化，无需更新。"}), 200 # 更改为 200 OK 状态码
        else:
            return jsonify({"message": "更新失败，未找到记录"}), 404

    except Exception as e:
        print(f"Error updating shipping cost for merchant: {e}")
        return jsonify({"message": f"服务器内部错误: {str(e)}"}), 500

# Removed SQLite initialization
if __name__ == '__main__':
    app.run(debug=False) # Set debug=False for production
