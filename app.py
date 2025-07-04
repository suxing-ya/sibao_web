#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于MySQL数据库的Flask应用主文件
替代原有的Supabase版本
"""

import os
import json
import uuid
import zipfile
import shutil
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
# 先加载临时环境变量设置
try:
    import temp_env  # 加载临时环境变量
except ImportError:
    pass

from db_mysql import db
import pymysql
# 移除密码加密相关导入，改为明文密码存储
from flask_mail import Mail, Message
import random
import string
import time

# 清除可能存在的旧环境变量
for key in list(os.environ.keys()):
    if key.startswith('DB_'):
        del os.environ[key]

# 强制重新加载环境变量
load_dotenv('.env', override=True)

app = Flask(__name__, template_folder='templates')
CORS(app, origins=["*"])  # 生产环境请指定具体域名

# Flask密钥配置
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY环境变量必须设置")

# 静态文件缓存配置
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# 邮件配置
app.config['MAIL_SERVER'] = 'smtp.qq.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'osibao@qq.com'
app.config['MAIL_PASSWORD'] = 'tskyrpiumteycach'
app.config['MAIL_DEFAULT_SENDER'] = 'osibao@qq.com'

# 初始化邮件
mail = Mail(app)

# 内存中存储验证码（生产环境建议使用Redis）
verification_codes = {}

# 测试数据库连接
print("开始测试MySQL数据库连接...")
print(f"数据库配置: host={db.config.get('host')}, user={db.config.get('user')}, database={db.config.get('database')}")

try:
    print("尝试创建连接...")
    with db.get_connection() as conn:
        print("✅ MySQL数据库连接成功")
except Exception as e:
    import traceback
    print(f"❌ MySQL数据库连接失败: {e}")
    print("详细错误信息:")
    traceback.print_exc()
    raise ValueError("请检查MySQL数据库连接配置")

# 添加日期时间格式化过滤器
@app.template_filter('datetime_format')
def datetime_format_filter(value, format="%Y-%m-%d %H:%M"):
    if not value:
        return ""
    if isinstance(value, str):
        try:
            dt_object = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return "无效日期"
        return dt_object.strftime(format)
    return str(value)

# 装饰器定义
def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            if request.is_json:
                return jsonify({"message": "未登录或会话已过期，请重新登录。"}), 401
            return redirect(url_for('user_login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理员权限装饰器 - 实时从数据库检查角色"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('user_login'))
        
        # 从数据库实时检查用户角色
        user_id = session.get('user_id')
        if not user_id:
            if request.is_json:
                return jsonify({"message": "用户会话无效，请重新登录。"}), 401
            return redirect(url_for('user_login'))
        
        try:
            # 查询用户最新角色
            user_data = db.execute_query(
                "SELECT role FROM profiles WHERE id = %s",
                [user_id],
                fetch_one=True
            )
            
            if not user_data:
                # 用户不存在，清除会话
                session.clear()
                if request.is_json:
                    return jsonify({"message": "用户不存在，请重新登录。"}), 401
                return redirect(url_for('user_login'))
            
            # 更新session中的角色信息
            session['role'] = user_data['role']
            
            if user_data['role'] != 'admin':
                if request.is_json:
                    return jsonify({"message": "权限不足，无权访问此功能。"}), 403
                return "权限不足", 403
                
        except Exception as e:
            print(f"管理员权限检查失败: {e}")
            if request.is_json:
                return jsonify({"message": "权限检查失败，请重试。"}), 500
            return "权限检查失败", 500
        
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission_key):
    """权限验证装饰器 - 实时从数据库检查权限"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                return redirect(url_for('user_login'))
            
            # 管理员默认拥有所有权限
            if session.get('role') == 'admin':
                return f(*args, **kwargs)
            
            # 从数据库实时获取用户最新权限
            user_id = session.get('user_id')
            if not user_id:
                if request.is_json:
                    return jsonify({"message": "用户会话无效，请重新登录。"}), 401
                return redirect(url_for('user_login'))
            
            try:
                # 查询用户最新权限
                user_data = db.execute_query(
                    "SELECT permissions, role FROM profiles WHERE id = %s",
                    [user_id],
                    fetch_one=True
                )
                
                if not user_data:
                    # 用户不存在，清除会话
                    session.clear()
                    if request.is_json:
                        return jsonify({"message": "用户不存在，请重新登录。"}), 401
                    return redirect(url_for('user_login'))
                
                # 检查用户角色是否变成管理员
                if user_data['role'] == 'admin':
                    # 更新session中的角色信息
                    session['role'] = 'admin'
                    return f(*args, **kwargs)
                
                # 解析权限
                user_permissions_str = user_data.get('permissions', '[]')
                try:
                    user_permissions = json.loads(user_permissions_str) if user_permissions_str else []
                    
                    # 更新session中的权限信息（可选，减少数据库查询）
                    session['permissions'] = user_permissions_str
                    
                    if permission_key not in user_permissions:
                        if request.is_json:
                            return jsonify({"message": f"权限不足，需要 '{permission_key}' 权限。请联系管理员分配权限。"}), 403
                        return "权限不足，请联系管理员分配权限", 403
                        
                except json.JSONDecodeError:
                    if request.is_json:
                        return jsonify({"message": "用户权限数据格式错误。"}), 403
                    return "权限数据错误", 403
                
            except Exception as e:
                print(f"权限检查失败: {e}")
                if request.is_json:
                    return jsonify({"message": "权限检查失败，请重试。"}), 500
                return "权限检查失败", 500
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 路由定义
@app.route('/')
def index():
    """首页"""
    if session.get('logged_in'):
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('pt_function_interface'))
    return render_template('index.html')

@app.route('/login', methods=['GET'])
def user_login():
    """用户登录页面"""
    return render_template('login.html')

@app.route('/register.html')
def user_register():
    """用户注册页面"""
    return render_template('register.html')

@app.route('/index.html')
def index_html():
    """首页HTML"""
    return render_template('index.html')

@app.route('/y2cost.html')
@login_required
@permission_required('y2cost_html')
def y2cost_html():
    """成本核算页面"""
    return render_template('y2cost.html')

@app.route('/barcode_generator.html')
@login_required
@permission_required('barcode_generator_html')
def barcode_generator_html():
    """条形码生成页面"""
    return render_template('barcode_generator.html')

@app.route('/api/barcode/upload_pdf', methods=['POST'])
@login_required
@permission_required('barcode_generator_html')
def api_upload_pdf():
    """
    上传PDF文件或ZIP压缩包
    支持多个PDF文件和ZIP文件自动解压
    """
    try:
        # 检查是否有文件上传
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'message': '没有选择文件'
            }), 400
        
        files = request.files.getlist('files')
        if not files or all(file.filename == '' for file in files):
            return jsonify({
                'success': False,
                'message': '没有选择有效文件'
            }), 400
        
        # 创建上传目录（所有文件存储在同一目录）
        upload_dir = os.path.join('uploads', 'pdf')
        
        # 确保目录存在
        os.makedirs(upload_dir, exist_ok=True)
        
        uploaded_files = []
        extracted_files = []
        errors = []
        
        for file in files:
            if file.filename == '':
                continue
                
            try:
                filename = secure_filename(file.filename)
                file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
                
                if file_ext == 'pdf':
                    # 处理PDF文件 - 直接保存，覆盖同名文件
                    file_path = os.path.join(upload_dir, filename)
                    file.save(file_path)
                    
                    uploaded_files.append({
                        'name': filename,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'type': 'pdf'
                    })
                    
                elif file_ext == 'zip':
                    # 处理ZIP文件
                    zip_path = os.path.join(upload_dir, filename)
                    file.save(zip_path)
                    
                    # 解压ZIP文件到临时目录
                    extract_dir = os.path.join(upload_dir, f"temp_extract_{filename.replace('.zip', '')}")
                    os.makedirs(extract_dir, exist_ok=True)
                    
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                    
                    # 查找解压出的PDF文件
                    for root, dirs, files_in_dir in os.walk(extract_dir):
                        for extracted_file in files_in_dir:
                            if extracted_file.lower().endswith('.pdf'):
                                extracted_path = os.path.join(root, extracted_file)
                                final_name = secure_filename(extracted_file)
                                final_path = os.path.join(upload_dir, final_name)
                                
                                # 直接移动文件，覆盖同名文件
                                shutil.move(extracted_path, final_path)
                                
                                extracted_files.append({
                                    'name': final_name,
                                    'path': final_path,
                                    'size': os.path.getsize(final_path),
                                    'type': 'pdf',
                                    'source_zip': filename
                                })
                    
                    # 清理临时解压目录和ZIP文件
                    shutil.rmtree(extract_dir, ignore_errors=True)
                    os.remove(zip_path)
                    
                else:
                    errors.append(f"不支持的文件格式: {filename}")
                    
            except Exception as e:
                errors.append(f"处理文件 {file.filename} 时出错: {str(e)}")
        
        # 合并上传和解压的文件
        all_files = uploaded_files + extracted_files
        
        return jsonify({
            'success': True,
            'message': f'成功处理 {len(all_files)} 个文件',
            'data': {
                'uploaded_files': all_files,
                'total_files': len(all_files),
                'errors': errors
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'上传失败: {str(e)}'
        }), 500

@app.route('/api/barcode/list_pdfs', methods=['GET'])
@login_required
@permission_required('barcode_generator_html')
def api_list_pdfs():
    """
    获取用户已上传的PDF文件列表
    """
    try:
        upload_dir = os.path.join('uploads', 'pdf')
        
        if not os.path.exists(upload_dir):
            return jsonify({
                'success': True,
                'data': {
                    'files': [],
                    'total_files': 0
                }
            })
        
        files = []
        for filename in os.listdir(upload_dir):
            if filename.lower().endswith('.pdf'):
                file_path = os.path.join(upload_dir, filename)
                if os.path.isfile(file_path):
                    files.append({
                        'name': filename,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'type': 'pdf',
                        'upload_time': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
                    })
        
        # 按上传时间排序
        files.sort(key=lambda x: x['upload_time'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': {
                'files': files,
                'total_files': len(files)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取文件列表失败: {str(e)}'
        }), 500

@app.route('/api/barcode/delete_pdf', methods=['DELETE'])
@login_required
@permission_required('barcode_generator_html')
def api_delete_pdf():
    """
    删除指定的PDF文件
    """
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({
                'success': False,
                'message': '文件名不能为空'
            }), 400
        
        upload_dir = os.path.join('uploads', 'pdf')
        file_path = os.path.join(upload_dir, secure_filename(filename))
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': '文件不存在'
            }), 404
        
        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'message': '文件删除成功'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'删除文件失败: {str(e)}'
        }), 500

@app.route('/api/barcode/clear_pdfs', methods=['DELETE'])
@login_required
@permission_required('barcode_generator_html')
def api_clear_pdfs():
    """
    清空用户所有上传的PDF文件
    """
    try:
        upload_dir = os.path.join('uploads', 'pdf')
        
        if os.path.exists(upload_dir):
            # 删除目录下所有PDF文件
            for filename in os.listdir(upload_dir):
                if filename.lower().endswith('.pdf'):
                    file_path = os.path.join(upload_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'message': '所有文件已清空'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'清空文件失败: {str(e)}'
        }), 500

@app.route('/api/barcode/extract_orders', methods=['POST'])
@login_required
@permission_required('barcode_generator_html')
def api_extract_orders():
    """
    从PDF文件中提取订单号
    这是一个简化的实现，实际应用中需要更复杂的PDF文本提取
    """
    try:
        data = request.get_json()
        filenames = data.get('filenames', [])
        
        if not filenames:
            return jsonify({
                'success': False,
                'message': '没有指定要处理的文件'
            }), 400
        
        upload_dir = os.path.join('uploads', 'pdf')
        
        extracted_orders = []
        processed_files = 0
        
        for filename in filenames:
            file_path = os.path.join(upload_dir, secure_filename(filename))
            
            if not os.path.exists(file_path):
                continue
            
            try:
                # 简化的订单号提取逻辑
                # 实际应用中需要使用PDF文本提取库如pdfplumber, PyPDF2等
                orders_from_filename = extract_orders_from_filename(filename)
                if orders_from_filename:
                    extracted_orders.extend(orders_from_filename)
                
                processed_files += 1
                
            except Exception as e:
                print(f"处理文件 {filename} 时出错: {e}")
                continue
        
        # 去重
        extracted_orders = list(set(extracted_orders))
        
        return jsonify({
            'success': True,
            'data': {
                'orders': extracted_orders,
                'total_orders': len(extracted_orders),
                'processed_files': processed_files
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'提取订单号失败: {str(e)}'
        }), 500

def extract_orders_from_filename(filename):
    """
    从文件名中提取可能的订单号
    这是一个简化的实现
    """
    import re
    
    # 移除文件扩展名
    name_without_ext = filename.replace('.pdf', '').replace('.PDF', '')
    
    orders = []
    
    # 常见订单号格式的正则表达式
    patterns = [
        r'PO[-_]?\d{3}[-_]?\d{10,}',  # PO-211-20713364403832603
        r'ORD[-_]?\d{8,}',            # ORD12345678
        r'\b\d{10,}\b',               # 10位以上数字
        r'[A-Z]{2,}\d{8,}'            # 字母+数字组合
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, name_without_ext, re.IGNORECASE)
        orders.extend(matches)
    
    return orders

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """管理员登录"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            # 从MySQL数据库查询用户（包含密码字段）
            user_data = db.execute_query(
                "SELECT id, username, password, role, permissions FROM profiles WHERE username = %s",
                [username],
                fetch_one=True
            )
            
            if user_data:
                # 验证密码（这里是明文比较，生产环境应该使用哈希密码）
                if user_data['password'] == password:
                    # 检查是否为管理员角色
                    if user_data['role'] == 'admin':
                        session['logged_in'] = True
                        session['user_id'] = user_data['id']
                        session['username'] = user_data['username']
                        session['role'] = user_data['role']
                        session['permissions'] = user_data['permissions'] if user_data['permissions'] else '[]'
                        return redirect(url_for('admin_dashboard'))
                    else:
                        return render_template('login_admin.html', login_error='没有管理员权限')
                else:
                    return render_template('login_admin.html', login_error='用户名或密码错误')
            else:
                return render_template('login_admin.html', login_error='用户不存在')
        except Exception as e:
            print(f"MySQL login error: {e}")
            return render_template('login_admin.html', login_error=f'登录失败: {e}')
    return render_template('login_admin.html')

@app.route('/admin/logout', methods=['GET', 'POST'])
def admin_logout():
    """管理员登出"""
    session.clear()
    
    # 如果是AJAX请求，返回JSON响应
    if request.headers.get('Content-Type') == 'application/json' or request.is_json:
        return jsonify({
            "success": True,
            "message": "管理员登出成功",
            "redirect_url": url_for('index')
        })
    
    # 如果是普通表单请求，返回重定向
    return redirect(url_for('index'))

@app.route('/api/send-verification-code', methods=['POST'])
def api_send_verification_code():
    """发送邮箱验证码API"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({
                'success': False,
                'message': '邮箱地址不能为空'
            }), 400
        
        # 验证邮箱格式
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({
                'success': False,
                'message': '邮箱格式不正确'
            }), 400
        
        # 检查邮箱是否已注册
        existing_user = db.execute_query(
            "SELECT id FROM profiles WHERE LOWER(username) = %s",
            [email],
            fetch_one=True
        )
        
        if existing_user:
            return jsonify({
                'success': False,
                'message': '该邮箱已被注册'
            }), 400
        
        # 生成6位数字验证码
        verification_code = ''.join(random.choices(string.digits, k=6))
        
        # 存储验证码（有效期5分钟）
        verification_codes[email] = {
            'code': verification_code,
            'timestamp': time.time(),
            'expires_at': time.time() + 300  # 5分钟后过期
        }
        
        # 发送邮件
        try:
            msg = Message(
                subject='【思宝】邮箱验证码',
                recipients=[email],
                html=f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center;">
                        <h2 style="color: #333; margin-bottom: 20px;">邮箱验证码</h2>
                        <p style="color: #666; font-size: 16px; margin-bottom: 30px;">
                            您正在注册思宝账户，请使用以下验证码完成注册：
                        </p>
                        <div style="background-color: #007bff; color: white; font-size: 32px; font-weight: bold; padding: 15px 30px; border-radius: 8px; letter-spacing: 5px; margin: 20px 0;">
                            {verification_code}
                        </div>
                        <p style="color: #999; font-size: 14px; margin-top: 30px;">
                            验证码有效期为5分钟，请尽快完成验证。<br>
                            如果这不是您本人操作，请忽略此邮件。
                        </p>
                    </div>
                </div>
                """
            )
            mail.send(msg)
            
            print(f"验证码已发送到 {email}: {verification_code}")
            
            return jsonify({
                'success': True,
                'message': '验证码已发送，请查收邮箱'
            })
            
        except Exception as e:
            print(f"邮件发送失败: {e}")
            return jsonify({
                'success': False,
                'message': '邮件发送失败，请重试'
            }), 500
            
    except Exception as e:
        print(f"发送验证码失败: {e}")
        return jsonify({
            'success': False,
            'message': f'发送验证码失败: {str(e)}'
        }), 500

@app.route('/api/register', methods=['POST'])
def api_register():
    """用户注册API - 注册到profiles表（需验证码）"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': '请提供有效的JSON数据'
            }), 400
        
        email = data.get('email', '').strip().lower()
        verification_code = data.get('verification_code', '').strip()
        password = data.get('password', '').strip()
        
        # 验证必需字段
        if not email or not verification_code or not password:
            return jsonify({
                'success': False,
                'message': '邮箱、验证码和密码都是必需的'
            }), 400
        
        # 验证邮箱格式
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({
                'success': False,
                'message': '邮箱格式不正确'
            }), 400
        
        # 验证密码强度
        if len(password) < 8:
            return jsonify({
                'success': False,
                'message': '密码长度至少为8位'
            }), 400
        
        # 验证验证码
        if email not in verification_codes:
            return jsonify({
                'success': False,
                'message': '验证码不存在或已过期，请重新发送'
            }), 400
        
        code_data = verification_codes[email]
        current_time = time.time()
        
        # 检查验证码是否过期
        if current_time > code_data['expires_at']:
            del verification_codes[email]
            return jsonify({
                'success': False,
                'message': '验证码已过期，请重新发送'
            }), 400
        
        # 检查验证码是否正确
        if verification_code != code_data['code']:
            return jsonify({
                'success': False,
                'message': '验证码错误'
            }), 400
        
        # 检查邮箱是否已存在
        existing_user = db.execute_query(
            "SELECT id FROM profiles WHERE LOWER(username) = %s",
            [email],
            fetch_one=True
        )
        
        if existing_user:
            return jsonify({
                'success': False,
                'message': '该邮箱已被注册'
            }), 400
        
        # 生成UUID作为用户ID
        user_id = str(uuid.uuid4())
        
        # 插入新用户到profiles表
        # 新注册用户没有任何权限，permissions为空数组
        # 密码以明文形式保存
        db.execute_insert(
            """
            INSERT INTO profiles (id, username, password, role, notes, permissions, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """,
            [user_id, email, password, 'user', f'邮箱: {email}', '[]']
        )
        
        # 注册成功后删除验证码
        del verification_codes[email]
        
        return jsonify({
            'success': True,
            'message': '注册成功，请联系管理员分配权限后使用',
            'user_id': user_id
        })
        
    except Exception as e:
        app.logger.error(f"用户注册失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'注册失败: {str(e)}'
        }), 500

@app.route('/api/check-permissions', methods=['GET'])
@login_required
def api_check_permissions():
    """检查当前用户权限状态API"""
    try:
        user_id = session.get('user_id')
        
        # 从数据库获取最新权限
        user_data = db.execute_query(
            "SELECT username, role, permissions FROM profiles WHERE id = %s",
            [user_id],
            fetch_one=True
        )
        
        if not user_data:
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 404
        
        # 更新session中的权限信息
        session['role'] = user_data['role']
        session['permissions'] = user_data.get('permissions', '[]')
        
        # 解析权限
        try:
            permissions = json.loads(user_data.get('permissions', '[]'))
        except:
            permissions = []
        
        return jsonify({
            'success': True,
            'data': {
                'username': user_data['username'],
                'role': user_data['role'],
                'permissions': permissions,
                'is_admin': user_data['role'] == 'admin'
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/post_login_callback', methods=['POST'])
def post_login_callback():
    """普通用户登录API（替代Supabase认证）"""
    try:
        data = request.get_json()
        # 支持用户名或邮箱登录
        username = data.get('username') or data.get('email')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"message": "用户名和密码不能为空"}), 400
            
        # 从MySQL数据库查询用户
        user_data = db.execute_query(
            "SELECT id, username, password, role, permissions FROM profiles WHERE username = %s",
            [username],
            fetch_one=True
        )
        
        if user_data and user_data['password'] == password:
            # 设置会话
            session['logged_in'] = True
            session['user_id'] = user_data['id']
            session['username'] = user_data['username']
            session['role'] = user_data['role']
            session['permissions'] = user_data['permissions'] if user_data['permissions'] else '[]'
            
            # 根据角色决定重定向页面
            if user_data['role'] == 'admin':
                redirect_url = url_for('admin_dashboard')
            else:
                redirect_url = url_for('pt_function_interface')
                
            return jsonify({
                "success": True,
                "message": "登录成功",
                "redirect_url": redirect_url
            })
        else:
            return jsonify({"message": "用户名或密码错误"}), 401
            
    except Exception as e:
        print(f"登录错误: {e}")
        return jsonify({"message": f"登录失败: {str(e)}"}), 500

@app.route('/logout', methods=['GET', 'POST'])
def user_logout():
    """用户登出"""
    session.clear()
    
    # 如果是AJAX请求，返回JSON响应
    if request.headers.get('Content-Type') == 'application/json' or request.is_json:
        return jsonify({
            "success": True,
            "message": "登出成功",
            "redirect_url": url_for('user_login')
        })
    
    # 如果是普通表单请求，返回重定向
    return redirect(url_for('user_login'))

# 业务页面路由
@app.route('/Expense Allocation Function.html')
@login_required
@permission_required('expense_allocation_function')
def expense_allocation_function():
    return render_template('Expense Allocation Function.html')

@app.route('/query.html')
@login_required
@permission_required('query_function')
def query_html():
    return render_template('query.html')

@app.route('/statisticaltable.html')
@login_required
@permission_required('statistical_function')
def statistical_table_html():
    """统计功能页面"""
    return render_template('statisticaltable.html')

@app.route('/temu-y2gzl.html')
@login_required
@permission_required('temu_y2gzl_html')
def temu_y2gzl_html():
    return render_template('temu-y2gzl.html')

@app.route('/ptfunctioninterface.html')
@login_required
def pt_function_interface():
    """用户功能界面"""
    try:
        # 获取当前用户信息
        user_id = session.get('user_id')
        user_data = db.execute_query(
            "SELECT id, username, role, created_at, notes, permissions FROM profiles WHERE id = %s",
            [user_id],
            fetch_one=True
        )
        
        if not user_data:
            session.clear()
            return redirect(url_for('user_login'))
        
        # 创建用户档案对象
        permissions_str = user_data.get('permissions')
        user_permissions = []
        if permissions_str and permissions_str.strip():
            try:
                user_permissions = json.loads(permissions_str)
            except json.JSONDecodeError:
                # 如果解析失败，打印一个警告，并使用空列表作为默认值
                print(f"警告: 用户(ID: {user_id})的权限字段JSON解析失败。内容为: '{permissions_str}'")
                user_permissions = []
        
        user_profile = {
            'id': user_data['id'],
            'username': user_data['username'],
            'email': f"{user_data['username']}@example.com",  # 模拟邮箱
            'role': user_data['role'],
            'created_at': user_data['created_at'],
            'notes': user_data.get('notes', ''),
            'permissions': user_permissions
        }
        
        # 定义功能列表
        functions = [
            {
                'name': '运费分摊核算',
                'description': '处理和分配运费成本',
                'url_route': 'expense_allocation_function',
                'required_permission': 'expense_allocation_function'
            },
            {
                'name': '统计功能',
                'description': '查看运费统计和报表',
                'url_route': 'statistical_table_html',
                'required_permission': 'statistical_function'
            },
            {
                'name': '成本核算',
                'description': 'Y2成本核算工具',
                'url_route': 'y2cost_html',
                'required_permission': 'y2cost_html'
            },
            {
                'name': '条形码生成',
                'description': '生成产品条形码',
                'url_route': 'barcode_generator_html',
                'required_permission': 'barcode_generator_html'
            },
            {
                'name': '货物工作流',
                'description': 'Temu平台运费计算工具',
                'url_route': 'temu_y2gzl_html',
                'required_permission': 'temu_y2gzl_html'
            },
            {
                'name': '查询功能',
                'description': '数据查询和检索',
                'url_route': 'query_html',
                'required_permission': 'query_function'  # 需要查询功能权限
            },
            {
                'name': 'OCR文字提取',
                'description': '从图片中识别和提取文字内容',
                'url_route': 'ocr_extract_html',
                'required_permission': 'ocr_extract_html'
            }
        ]
        
        return render_template('ptfunctioninterface.html', 
                             user_profile=user_profile, 
                             functions=functions)
                             
    except Exception as e:
        print(f"用户界面加载错误: {e}")
        return render_template('ptfunctioninterface.html', 
                             user_profile={'username': session.get('username', '未知用户'), 'role': 'user', 'email': '', 'created_at': '', 'notes': '', 'permissions': []}, 
                             functions=[])

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """管理员仪表板"""
    try:
        # 从MySQL数据库获取用户档案数据
        profiles = db.execute_query(
            "SELECT id, username, created_at, role, notes, permissions FROM profiles ORDER BY created_at DESC"
        )
        
        # 从MySQL数据库获取商家数据
        merchants = db.execute_query(
            "SELECT id, merchant_code, merchant_name, merchant_id_code, created_at FROM merchants ORDER BY merchant_id_code ASC"
        )
        
        # 格式化数据以匹配前端需求
        members = []
        if profiles:
            for profile in profiles:
                # 安全处理权限数据
                permissions_str = profile.get('permissions', '[]')
                try:
                    # 验证权限字段是否为有效JSON
                    if permissions_str:
                        json.loads(permissions_str)  # 验证JSON格式
                except:
                    permissions_str = '[]'  # 如果格式错误，默认为空数组
                    
                # 确保权限数据格式正确
                try:
                    # 尝试解析并重新序列化，确保格式统一
                    if permissions_str and permissions_str != '[]':
                        parsed_permissions = json.loads(permissions_str)
                        permissions_str = json.dumps(parsed_permissions)
                    else:
                        permissions_str = '[]'
                except:
                    permissions_str = '[]'
                
                print(f"用户 {profile['username']} 权限数据: {permissions_str}")
                
                # 解析权限为数组，便于前端处理
                try:
                    permissions_array = json.loads(permissions_str) if permissions_str != '[]' else []
                except:
                    permissions_array = []
                
                members.append({
                    'id': profile['id'],
                    'username': profile['username'],
                    'email': f"{profile['username']}@example.com",  # 临时邮箱
                    'role': profile['role'],
                    'registered_at': profile['created_at'],
                    'notes': profile.get('notes', 'N/A'),
                    'permissions': permissions_str,  # 保留原JSON字符串
                    'permissions_array': permissions_array  # 添加解析后的数组
                })
        
        data = {
            'profiles': profiles if profiles else [],
            'merchants': merchants if merchants else []
        }
        
        return render_template('admin.html', members=members, data=data, session=session)
    except Exception as e:
        print(f"Admin dashboard error: {e}")
        return render_template('admin.html', error=str(e), members=[], data={'profiles':[], 'merchants':[]})

# API路由
@app.route('/api/merchants', methods=['GET'])
@login_required
def api_get_merchants():
    """获取商家列表API"""
    try:
        search_term = request.args.get('search', '')
        merchants = db.get_merchants(search_term)
        return jsonify({"success": True, "data": merchants})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/merchants', methods=['POST'])
@login_required
@admin_required
def api_create_merchant():
    """创建商家API"""
    try:
        data = request.get_json()
        merchant_code = data.get('merchant_code')
        merchant_name = data.get('merchant_name')
        merchant_id_code = data.get('merchant_id_code')
        
        if not all([merchant_code, merchant_name, merchant_id_code]):
            return jsonify({"success": False, "message": "缺少必要字段"}), 400
        
        # 检查是否已存在
        existing = db.execute_query(
            "SELECT id FROM merchants WHERE merchant_code = %s OR merchant_id_code = %s",
            [merchant_code, merchant_id_code],
            fetch_one=True
        )
        
        if existing:
            return jsonify({"success": False, "message": "商家代号或编号已存在"}), 400
        
        # 插入新商家
        result = db.execute_insert(
            "INSERT INTO merchants (merchant_code, merchant_name, merchant_id_code, created_at) VALUES (%s, %s, %s, NOW())",
            [merchant_code, merchant_name, merchant_id_code]
        )
        
        print(f"新增商家成功: {merchant_id_code} - {merchant_code} ({merchant_name}), 插入ID: {result}")
        
        return jsonify({"success": True, "message": "商家创建成功"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/merchants/<int:merchant_id>', methods=['PUT'])
@login_required
@admin_required
def api_update_merchant(merchant_id):
    """更新商家API"""
    try:
        data = request.get_json()
        merchant_code = data.get('merchant_code')
        merchant_name = data.get('merchant_name')
        merchant_id_code = data.get('merchant_id_code')
        
        if not all([merchant_code, merchant_name, merchant_id_code]):
            return jsonify({"success": False, "message": "缺少必要字段"}), 400
        
        # 检查是否存在重复（排除当前记录）
        existing = db.execute_query(
            "SELECT id FROM merchants WHERE (merchant_code = %s OR merchant_id_code = %s) AND id != %s",
            [merchant_code, merchant_id_code, merchant_id],
            fetch_one=True
        )
        
        if existing:
            return jsonify({"success": False, "message": "商家代号或编号已存在"}), 400
        
        # 更新商家
        rows_affected = db.execute_update(
            "UPDATE merchants SET merchant_code = %s, merchant_name = %s, merchant_id_code = %s WHERE id = %s",
            [merchant_code, merchant_name, merchant_id_code, merchant_id]
        )
        
        if rows_affected > 0:
            print(f"更新商家成功: {merchant_id_code} - {merchant_code} ({merchant_name})")
            return jsonify({"success": True, "message": "商家更新成功"})
        else:
            return jsonify({"success": False, "message": "商家不存在"}), 404
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/merchants/<int:merchant_id>', methods=['DELETE'])
@login_required
@admin_required
def api_delete_merchant(merchant_id):
    """删除商家API"""
    try:
        # 删除商家
        rows_affected = db.execute_delete(
            "DELETE FROM merchants WHERE id = %s",
            [merchant_id]
        )
        
        if rows_affected > 0:
            print(f"删除商家成功: ID {merchant_id}")
            return jsonify({"success": True, "message": "商家删除成功"})
        else:
            return jsonify({"success": False, "message": "商家不存在"}), 404
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/users', methods=['POST'])
@login_required
@admin_required
def api_create_user():
    """创建子账号API"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        role = data.get('role', 'user')
        notes = data.get('notes', '')
        
        if not all([username, password]):
            return jsonify({"success": False, "message": "用户名和密码不能为空"}), 400
        
        # 检查用户名是否已存在
        existing = db.execute_query(
            "SELECT id FROM profiles WHERE username = %s",
            [username],
            fetch_one=True
        )
        
        if existing:
            return jsonify({"success": False, "message": "用户名已存在"}), 400
        
        # 插入新用户
        user_id = str(uuid.uuid4())
        db.execute_insert(
            "INSERT INTO profiles (id, username, password, role, notes, permissions, created_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
            [user_id, username, password, role, notes, '[]']
        )
        
        print(f"新增子账号成功: {username} ({role})")
        return jsonify({"success": True, "message": "子账号创建成功"})
        
    except Exception as e:
        print(f"创建子账号失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/member/<string:member_id>/permissions', methods=['PUT'])
@login_required
@admin_required
def api_update_member_permissions(member_id):
    """更新用户权限API"""
    try:
        print(f"权限更新请求 - 用户ID: {member_id} (类型: {type(member_id)})")
        
        data = request.get_json()
        permissions = data.get('permissions', [])
        print(f"请求的权限列表: {permissions}")
        
        # 验证权限列表
        valid_permissions = [
            'y2cost_html',
            'temu_y2gzl_html', 
            'expense_allocation_function',
            'barcode_generator_html',
            'statistical_function',
            'query_function',
            'product_extractor_html'
        ]
        
        # 过滤无效权限
        filtered_permissions = [p for p in permissions if p in valid_permissions]
        print(f"过滤后权限列表: {filtered_permissions}")
        
        # 先检查用户是否存在
        user_check = db.execute_query(
            "SELECT id, username FROM profiles WHERE id = %s",
            [member_id],
            fetch_one=True
        )
        
        print(f"用户检查结果: {user_check}")
        
        if not user_check:
            print(f"用户不存在: ID = {member_id}")
            return jsonify({"success": False, "message": f"用户不存在 (ID: {member_id})"}), 404
        
        # 更新用户权限
        permissions_json = json.dumps(filtered_permissions)
        print(f"即将保存的权限JSON: {permissions_json}")
        
        # 尝试不同的更新方式来解决权限更新问题
        try:
            # 方法1: 使用标准的UUID字符串匹配
            rows_affected = db.execute_update(
                "UPDATE profiles SET permissions = %s WHERE id = %s",
                [permissions_json, member_id]
            )
            print(f"标准更新: {rows_affected} 行受影响")
            
            if rows_affected == 0:
                # 方法2: 先查询确认用户存在并获取确切的ID格式
                existing_user = db.execute_query(
                    "SELECT id, username FROM profiles WHERE id = %s",
                    [member_id],
                    fetch_one=True
                )
                print(f"用户查询结果: {existing_user}")
                
                if existing_user:
                    # 如果用户存在，直接用查询到的ID进行更新
                    exact_id = existing_user['id']
                    rows_affected = db.execute_update(
                        "UPDATE profiles SET permissions = %s WHERE id = %s",
                        [permissions_json, exact_id]
                    )
                    print(f"精确ID更新: {rows_affected} 行受影响")
                
            if rows_affected == 0:
                # 方法3: 如果还是失败，尝试用用户名更新
                user_check = db.execute_query(
                    "SELECT username FROM profiles WHERE id = %s",
                    [member_id],
                    fetch_one=True
                )
                if user_check:
                    username = user_check['username']
                    rows_affected = db.execute_update(
                        "UPDATE profiles SET permissions = %s WHERE username = %s",
                        [permissions_json, username]
                    )
                    print(f"用户名更新: {rows_affected} 行受影响")
                    
        except Exception as e:
            print(f"数据库更新异常: {e}")
            rows_affected = 0
        
        print(f"更新结果: {rows_affected} 行受影响")
        
        if rows_affected > 0:
            print(f"用户权限更新成功: ID {member_id}, 权限: {filtered_permissions}")
            return jsonify({"success": True, "message": "权限更新成功"})
        else:
            print(f"权限更新失败: 没有行被更新")
            return jsonify({"success": False, "message": "权限更新失败，没有行被更新"}), 404
            
    except Exception as e:
        print(f"更新用户权限失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/member/<string:member_id>', methods=['PUT'])
@login_required
@admin_required
def api_update_member(member_id):
    """更新用户密码和备注API"""
    try:
        data = request.get_json()
        password = data.get('password')
        notes = data.get('notes', '')
        
        if not password:
            return jsonify({"success": False, "message": "密码不能为空"}), 400
        
        if len(password) < 6:
            return jsonify({"success": False, "message": "密码长度至少为6位"}), 400
        
        # 检查用户是否存在
        existing_user = db.execute_query(
            "SELECT id, role, username FROM profiles WHERE id = %s",
            [member_id],
            fetch_one=True
        )
        
        if not existing_user:
            return jsonify({"success": False, "message": "用户不存在"}), 404
        
        # 防止修改管理员账户
        if existing_user['role'] == 'admin':
            return jsonify({"success": False, "message": "不能修改管理员账户"}), 403
        
        # 更新用户密码和备注（明文保存密码）
        rows_affected = db.execute_update(
            "UPDATE profiles SET password = %s, notes = %s WHERE id = %s",
            [password, notes, member_id]
        )
        
        if rows_affected > 0:
            print(f"更新用户密码和备注成功: {existing_user['username']} (ID: {member_id})")
            return jsonify({"success": True, "message": "用户密码和备注更新成功"})
        else:
            return jsonify({"success": False, "message": "更新失败"}), 400
            
    except Exception as e:
        print(f"更新用户失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/member/<string:member_id>', methods=['DELETE'])
@login_required
@admin_required  
def api_delete_member(member_id):
    """删除用户API"""
    try:
        # 不能删除管理员账户
        user_data = db.execute_query(
            "SELECT role FROM profiles WHERE id = %s",
            [member_id],
            fetch_one=True
        )
        
        if not user_data:
            return jsonify({"success": False, "message": "用户不存在"}), 404
        
        if user_data['role'] == 'admin':
            return jsonify({"success": False, "message": "不能删除管理员账户"}), 403
        
        # 删除用户
        rows_affected = db.execute_delete(
            "DELETE FROM profiles WHERE id = %s",
            [member_id]
        )
        
        if rows_affected > 0:
            print(f"删除用户成功: ID {member_id}")
            return jsonify({"success": True, "message": "用户删除成功"})
        else:
            return jsonify({"success": False, "message": "删除失败"}), 500
            
    except Exception as e:
        print(f"删除用户失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/shipping_costs', methods=['GET'])
@login_required
def api_get_shipping_costs():
    """获取运费成本数据API"""
    try:
        filters = {}
        
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        if request.args.get('tracking_numbers'):
            filters['tracking_numbers'] = request.args.get('tracking_numbers').split(',')
        if request.args.get('merchant_name'):
            filters['merchant_name'] = request.args.get('merchant_name')
        
        shipping_costs = db.get_shipping_costs(filters)
        return jsonify({"success": True, "data": shipping_costs})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/shipping_costs', methods=['POST'])
@login_required
@permission_required('expense_allocation_function')
def api_save_shipping_cost():
    """保存运费成本数据API"""
    try:
        data = request.get_json()
        db.save_shipping_cost(data)
        return jsonify({"success": True, "message": "数据保存成功"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/shipping_costs/<string:cost_id>', methods=['DELETE'])
@login_required
@permission_required('query_function')
def api_delete_shipping_cost(cost_id):
    """删除运费记录API"""
    try:
        # 检查记录是否存在
        existing_record = db.execute_query(
            "SELECT id FROM shipping_costs WHERE id = %s",
            [cost_id],
            fetch_one=True
        )
        
        if not existing_record:
            return jsonify({"success": False, "message": "记录不存在"}), 404
        
        # 删除记录
        rows_affected = db.execute_update(
            "DELETE FROM shipping_costs WHERE id = %s",
            [cost_id]
        )
        
        if rows_affected > 0:
            return jsonify({"success": True, "message": "删除成功"})
        else:
            return jsonify({"success": False, "message": "删除失败"}), 500
        
    except Exception as e:
        print(f"删除运费数据错误: {e}")
        return jsonify({"success": False, "message": f"删除失败: {str(e)}"}), 500

@app.route('/api/shipping_costs/update', methods=['PUT'])
@login_required
@permission_required('statistical_function')
def update_shipping_cost():
    """更新运费成本数据API"""
    try:
        data = request.get_json()
        item_id = data.get('id')
        merchant_name = data.get('merchant_name')
        tax_unit_price = data.get('tax_unit_price')
        operating_fee = data.get('operating_fee')
        total_overall = data.get('total_overall')

        if not item_id or merchant_name is None:
            return jsonify({"message": "缺少必要的参数：ID 或商家名称"}), 400

        # 获取当前数据
        current_data = db.execute_query(
            "SELECT merchants FROM shipping_costs WHERE id = %s",
            [item_id],
            fetch_one=True
        )

        if not current_data:
            return jsonify({"message": "未找到对应的数据"}), 404

        # 解析merchants JSON
        current_merchants = json.loads(current_data['merchants']) if current_data['merchants'] else []
        updated_merchants = []
        merchant_found = False

        for merchant in current_merchants:
            if merchant.get('name') == merchant_name:
                # 更新匹配的商家数据
                merchant['tax_unit_price'] = tax_unit_price
                merchant['operating_fee'] = operating_fee
                merchant['total_overall'] = total_overall
                merchant_found = True
            updated_merchants.append(merchant)

        if not merchant_found:
            print(f"Warning: Merchant {merchant_name} not found in existing merchants array for ID {item_id}")

        # 更新数据库
        db.execute_update(
            "UPDATE shipping_costs SET merchants = %s WHERE id = %s",
            [json.dumps(updated_merchants), item_id]
        )

        return jsonify({"message": "数据更新成功！"}), 200
    except Exception as e:
        print(f"Exception in update_shipping_cost: {e}")
        return jsonify({"message": "服务器内部错误"}), 500

@app.route('/api/shipping_costs/update_settlement_status', methods=['PUT'])
@login_required
@permission_required('statistical_function')
def update_settlement_status():
    """更新结算状态API"""
    try:
        data = request.get_json()
        item_id = data.get('id')
        new_status = data.get('settlement_status')

        if not item_id or not new_status:
            return jsonify({"success": False, "message": "缺少必要的参数。"}), 400

        rows_affected = db.update_settlement_status(item_id, new_status)
        
        if rows_affected > 0:
            return jsonify({"success": True, "message": "结算状态更新成功。"}), 200
        else:
            return jsonify({"success": False, "message": "未找到对应的记录或状态未发生变化。"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ==========================================
# 新的发货费用分摊表API接口
# ==========================================

@app.route('/api/shipping_allocations', methods=['POST'])
@login_required
@permission_required('expense_allocation_function')
def api_save_shipping_allocation():
    """
    保存发货费用分摊数据API (新版本)
    
    数据格式:
    {
        "date": "2025-01-15",
        "order_number": "SA20250115001",
        "tracking_number": "SF1234567890",
        "shipment_id": "SP2025011501",
        "freight_unit_price": 60.00,
        "box_count": 5,
        "total_settle_weight": 38.000,
        "actual_weight_with_box": 35.000,
        "merchants": [
            {
                "merchant_name": "陈芬芬",
                "pieces": 10,
                "weight": 10.000,
                "weight_ratio": 33.33,
                "box_weight": 1.667,
                "throw_weight": 1.000,
                "settle_weight": 12.667,
                "amount": 760.00
            }
        ]
    }
    """
    try:
        data = request.get_json()
        
        # 验证必要字段
        required_fields = ['date', 'order_number', 'freight_unit_price', 'merchants']
        for field in required_fields:
            if field not in data or data[field] is None:
                return jsonify({"success": False, "message": f"缺少必要字段: {field}"}), 400
        
        # 验证商户数据
        merchants = data.get('merchants', [])
        if not merchants:
            return jsonify({"success": False, "message": "至少需要一个商户记录"}), 400
        
        for i, merchant in enumerate(merchants):
            if not merchant.get('merchant_name'):
                return jsonify({"success": False, "message": f"第{i+1}个商户缺少商户名称"}), 400
        
        # 保存数据到新的表结构
        main_id = db.save_shipping_allocation(data)
        
        return jsonify({
            "success": True, 
            "message": "发货费用分摊数据保存成功",
            "main_id": main_id
        })
        
    except Exception as e:
        print(f"保存发货费用分摊数据失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/shipping_allocations', methods=['GET'])
@login_required
@permission_required('query_function')
def api_get_shipping_allocations():
    """
    获取发货费用分摊数据API (新版本)
    
    查询参数:
    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    - order_numbers: 订单号列表 (逗号分隔)
    - order_number_prefix: 订单号前缀
    - tracking_number: 单个快递单号 (兼容)
    - tracking_numbers: 多个快递单号 (逗号分隔)
    """
    try:
        filters = {}
        
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        if request.args.get('order_numbers'):
            filters['order_numbers'] = request.args.get('order_numbers').split(',')
        if request.args.get('order_number_prefix'):
            filters['order_number_prefix'] = request.args.get('order_number_prefix')
        
        # 处理快递单号查询（支持单个和多个）
        if request.args.get('tracking_numbers'):
            # 多个快递单号（新功能）
            tracking_numbers = [num.strip() for num in request.args.get('tracking_numbers').split(',') if num.strip()]
            if tracking_numbers:
                filters['tracking_numbers'] = tracking_numbers
        elif request.args.get('tracking_number'):
            # 单个快递单号（向后兼容）
            filters['tracking_numbers'] = [request.args.get('tracking_number')]
        
        allocations = db.get_shipping_allocations(filters)
        
        # 格式化日期字段，确保前端能正确处理
        formatted_allocations = []
        for allocation in allocations:
            formatted_allocation = dict(allocation)
            if formatted_allocation.get('date'):
                # 将日期转换为YYYY-MM-DD格式
                if hasattr(formatted_allocation['date'], 'strftime'):
                    formatted_allocation['date'] = formatted_allocation['date'].strftime('%Y-%m-%d')
                elif isinstance(formatted_allocation['date'], str) and len(formatted_allocation['date']) >= 10:
                    # 如果已经是字符串，只取前10位
                    formatted_allocation['date'] = formatted_allocation['date'][:10]
            
            # 格式化商户数据中的数值字段
            if 'merchants' in formatted_allocation:
                for merchant in formatted_allocation['merchants']:
                    # 确保数值字段为float类型而不是Decimal
                    for field in ['actual_weight', 'weight_ratio', 'box_weight', 'throw_weight', 'settle_weight', 'amount']:
                        if field in merchant and merchant[field] is not None:
                            merchant[field] = float(merchant[field])
            
            formatted_allocations.append(formatted_allocation)
        
        return jsonify({
            "success": True, 
            "data": formatted_allocations,
            "count": len(formatted_allocations)
        })
        
    except Exception as e:
        print(f"获取发货费用分摊数据失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/shipping_allocations/<string:order_number>', methods=['GET'])
@login_required
@permission_required('query_function')
def api_get_shipping_allocation_by_order(order_number):
    """根据订单号获取单条发货费用分摊记录API"""
    try:
        allocation = db.get_shipping_allocation_by_order_number(order_number)
        
        if not allocation:
            return jsonify({"success": False, "message": "未找到对应的记录"}), 404
        
        # 格式化日期字段，确保前端日期输入框能正确显示
        formatted_allocation = dict(allocation)
        if formatted_allocation.get('date'):
            # 将日期转换为YYYY-MM-DD格式
            if hasattr(formatted_allocation['date'], 'strftime'):
                formatted_allocation['date'] = formatted_allocation['date'].strftime('%Y-%m-%d')
            elif isinstance(formatted_allocation['date'], str) and len(formatted_allocation['date']) >= 10:
                # 如果已经是字符串，只取前10位
                formatted_allocation['date'] = formatted_allocation['date'][:10]
        
        # 格式化商户数据中的数值字段，确保精度一致
        if 'merchants' in formatted_allocation:
            for merchant in formatted_allocation['merchants']:
                # 确保数值字段为float类型而不是Decimal
                for field in ['actual_weight', 'weight_ratio', 'box_weight', 'throw_weight', 'settle_weight', 'amount']:
                    if field in merchant and merchant[field] is not None:
                        merchant[field] = float(merchant[field])
        
        return jsonify({
            "success": True, 
            "data": formatted_allocation
        })
        
    except Exception as e:
        print(f"获取发货费用分摊记录失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/shipping_allocations/<int:main_id>', methods=['DELETE'])
@login_required
@permission_required('expense_allocation_function')
def api_delete_shipping_allocation(main_id):
    """删除发货费用分摊记录API (软删除)"""
    try:
        rows_affected = db.delete_shipping_allocation(main_id)
        
        if rows_affected > 0:
            return jsonify({
                "success": True, 
                "message": "发货费用分摊记录删除成功"
            })
        else:
            return jsonify({
                "success": False, 
                "message": "未找到对应的记录"
            }), 404
            
    except Exception as e:
        print(f"删除发货费用分摊记录失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/shipping_allocations/statistics', methods=['GET'])
@login_required
@permission_required('statistical_function')
def api_get_allocation_statistics():
    """
    获取发货费用分摊统计数据API
    
    查询参数:
    - start_date: 开始日期
    - end_date: 结束日期
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        statistics = db.get_allocation_statistics(start_date, end_date)
        
        return jsonify({
            "success": True, 
            "data": statistics
        })
        
    except Exception as e:
        print(f"获取统计数据失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/shipping_allocations/merchant_summary', methods=['GET'])
@login_required
@permission_required('statistical_function')
def api_get_merchant_allocation_summary():
    """
    获取商户费用分摊汇总API
    
    查询参数:
    - merchant_name: 商户名称
    - start_date: 开始日期
    - end_date: 结束日期
    """
    try:
        merchant_name = request.args.get('merchant_name')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        summary = db.get_merchant_allocation_summary(merchant_name, start_date, end_date)
        
        return jsonify({
            "success": True, 
            "data": summary,
            "count": len(summary)
        })
        
    except Exception as e:
        print(f"获取商户汇总数据失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# 向后兼容的API (可选保留)
@app.route('/api/shipping_allocations/load_data', methods=['GET'])
@login_required
@permission_required('query_function')
def api_load_allocation_data():
    """
    为前端页面加载数据的兼容API
    根据order_number参数返回对应的分摊数据
    """
    try:
        order_number = request.args.get('order_number')
        
        if not order_number:
            return jsonify({"success": False, "message": "缺少order_number参数"}), 400
        
        allocation = db.get_shipping_allocation_by_order_number(order_number)
        
        if not allocation:
            return jsonify({
                "success": True, 
                "message": "未找到数据，返回空数据",
                "data": None
            })
        
        # 转换数据格式以兼容前端
        response_data = {
            "date": allocation['date'].strftime('%Y-%m-%d') if allocation['date'] else '',
            "order_number": allocation['order_number'],
            "tracking_number": allocation['tracking_number'] or '',
            "shipment_id": allocation['shipment_id'] or '',
            "freight_unit_price": float(allocation['freight_unit_price']),
            "box_count": allocation['box_count'],
            "total_settle_weight": float(allocation['total_settle_weight']),
            "actual_weight_with_box": float(allocation['actual_weight_with_box']),
            "merchants": []
        }
        
        # 转换商户数据
        for merchant in allocation.get('merchants', []):
            merchant_data = {
                "merchant_name": merchant['merchant_name'],
                "pieces": merchant['pieces'],
                "weight": float(merchant['actual_weight']),
                "weight_ratio": float(merchant['weight_ratio']),
                "box_weight": float(merchant['box_weight']),
                "throw_weight": float(merchant['throw_weight']),
                "settle_weight": float(merchant['settle_weight']),
                "amount": float(merchant['amount'])
            }
            response_data["merchants"].append(merchant_data)
        
        return jsonify({
            "success": True, 
            "data": response_data
        })
        
    except Exception as e:
        print(f"加载分摊数据失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/shipping_allocations/<order_number>', methods=['PUT'])
def update_shipping_allocation(order_number):
    """
    更新指定order_number的发货费用分摊数据
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': '请提供有效的JSON数据'
            }), 400
        
        # 验证必需字段
        required_fields = ['date', 'order_number']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'message': f'缺少必需字段: {field}'
                }), 400
        
        # 确保order_number匹配
        if data['order_number'] != order_number:
            return jsonify({
                'success': False,
                'message': 'URL中的order_number与数据中的order_number不匹配'
            }), 400
        
        # 更新主记录
        main_id = db.update_shipping_allocation_main(
            order_number=order_number,
            date=data['date'],
            freight_unit_price=data.get('freight_unit_price', 0),
            total_settle_weight=data.get('total_settle_weight', 0),
            actual_weight_with_box=data.get('actual_weight_with_box', 0),
            tracking_number=data.get('tracking_number', ''),
            shipment_id=data.get('shipment_id', ''),
            box_count=data.get('box_count', 0)
        )
        
        if not main_id:
            return jsonify({
                'success': False,
                'message': '未找到要更新的记录'
            }), 404
        
        # 删除旧的明细记录
        db.delete_shipping_allocation_details_by_main_id(main_id)
        
        # 添加新的明细记录
        merchants = data.get('merchants', [])
        for merchant in merchants:
            db.insert_shipping_allocation_detail(
                main_id=main_id,
                merchant_name=merchant.get('merchant_name', ''),
                pieces=merchant.get('pieces', 1),
                actual_weight=merchant.get('weight', 0),
                weight_ratio=merchant.get('weight_ratio', 0),
                box_weight=merchant.get('box_weight', 0),
                throw_weight=merchant.get('throw_weight', 0),
                settle_weight=merchant.get('settle_weight', 0),
                amount=merchant.get('amount', 0)
            )
        
        # 记录历史
        db.insert_shipping_allocation_history(
            main_id=main_id,
            operation_type='UPDATE',
            operation_data=json.dumps(data, ensure_ascii=False, default=str)
        )
        
        return jsonify({
            'success': True,
            'message': '分摊数据更新成功',
            'main_id': main_id
        })
        
    except Exception as e:
        app.logger.error(f"更新分摊数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }), 500

# TEMU工作流相关API
@app.route('/api/temu_workflow', methods=['GET'])
@login_required
@permission_required('temu_y2gzl_html')
def api_get_temu_workflow():
    """
    获取TEMU工作流数据API
    
    查询参数:
    - date_range: 日期范围 (7 表示最近7天, 10 表示最近10天)
    - main_tracking_id: 主运单号
    - status: 状态
    """
    try:
        filters = {}
        
        date_range = request.args.get('date_range')
        if date_range:
            filters['date_range'] = int(date_range)
            
        main_tracking_id = request.args.get('main_tracking_id')
        if main_tracking_id:
            filters['main_tracking_id'] = main_tracking_id
            
        status = request.args.get('status')
        if status:
            filters['status'] = status
        
        # 分页参数
        page = int(request.args.get('page', 0))
        limit = int(request.args.get('limit', 12))
        
        workflow_data = db.get_temu_workflow(filters)
        
        # 计算分页
        total_count = len(workflow_data)
        start_idx = page * limit
        end_idx = start_idx + limit
        paginated_data = workflow_data[start_idx:end_idx]
        
        return jsonify({
            "success": True, 
            "data": paginated_data,
            "count": len(paginated_data),
            "total_count": total_count,
            "page": page,
            "limit": limit
        })
        
    except Exception as e:
        print(f"获取TEMU工作流数据失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/temu_workflow', methods=['POST'])
@login_required
@permission_required('temu_y2gzl_html')
def api_save_temu_workflow():
    """创建新的TEMU工作流记录"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "message": "请提供有效的JSON数据"}), 400
        
        # 插入数据到数据库
        sql = """
        INSERT INTO temu_workflow (
            cn_send_date, main_tracking_id, box_code, box_count,
            inner_count, status, us_receive_date, us_box_count,
            us_actual_count
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = [
            data.get('cn_send_date'),
            data.get('main_tracking_id'),
            data.get('box_code'),
            data.get('box_count'),
            data.get('inner_count'),
            data.get('status'),
            data.get('us_receive_date'),
            data.get('us_box_count'),
            data.get('us_actual_count')
        ]
        
        result_id = db.execute_insert(sql, params)
        
        return jsonify({
            "success": True,
            "message": "TEMU工作流记录创建成功",
            "id": result_id
        })
        
    except Exception as e:
        print(f"创建TEMU工作流记录失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/temu_workflow/<int:workflow_id>', methods=['PUT'])
@login_required
@permission_required('temu_y2gzl_html')
def api_update_temu_workflow(workflow_id):
    """更新TEMU工作流记录"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "message": "请提供有效的JSON数据"}), 400
        
        # 更新数据库记录
        sql = """
        UPDATE temu_workflow SET
            cn_send_date = %s, main_tracking_id = %s, box_code = %s,
            box_count = %s, inner_count = %s, status = %s,
            us_receive_date = %s, us_box_count = %s, us_actual_count = %s
        WHERE id = %s
        """
        
        params = [
            data.get('cn_send_date'),
            data.get('main_tracking_id'),
            data.get('box_code'),
            data.get('box_count'),
            data.get('inner_count'),
            data.get('status'),
            data.get('us_receive_date'),
            data.get('us_box_count'),
            data.get('us_actual_count'),
            workflow_id
        ]
        
        rows_affected = db.execute_update(sql, params)
        
        if rows_affected > 0:
            return jsonify({
                "success": True,
                "message": "TEMU工作流记录更新成功"
            })
        else:
            return jsonify({
                "success": False,
                "message": "未找到要更新的记录"
            }), 404
        
    except Exception as e:
        print(f"更新TEMU工作流记录失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/temu_workflow/<int:workflow_id>', methods=['DELETE'])
@login_required
@permission_required('temu_y2gzl_html')
def api_delete_temu_workflow(workflow_id):
    """删除TEMU工作流记录"""
    try:
        rows_affected = db.execute_delete(
            "DELETE FROM temu_workflow WHERE id = %s",
            [workflow_id]
        )
        
        if rows_affected > 0:
            return jsonify({
                "success": True,
                "message": "TEMU工作流记录删除成功"
            })
        else:
            return jsonify({
                "success": False,
                "message": "未找到要删除的记录"
            }), 404
        
    except Exception as e:
        print(f"删除TEMU工作流记录失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# TEMU货件ID相关API
@app.route('/api/temu_shipment_ids', methods=['GET'])
@login_required
@permission_required('temu_y2gzl_html')
def api_get_temu_shipment_ids():
    """获取TEMU货件ID数据"""
    try:
        workflow_id = request.args.get('workflow_id')
        if not workflow_id:
            return jsonify({"success": False, "message": "缺少workflow_id参数"}), 400
        
        sql = "SELECT id, shipment_id_value FROM temu_shipment_ids WHERE workflow_id = %s ORDER BY id ASC"
        shipment_ids = db.execute_query(sql, [workflow_id])
        
        return jsonify({
            "success": True, 
            "data": shipment_ids
        })
        
    except Exception as e:
        print(f"获取TEMU货件ID数据失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# TEMU发货明细相关API
@app.route('/api/temu_shipment_details', methods=['GET'])
@login_required
@permission_required('temu_y2gzl_html')
def api_get_temu_shipment_details():
    """获取TEMU发货明细数据"""
    try:
        workflow_id = request.args.get('workflow_id')
        if not workflow_id:
            return jsonify({"success": False, "message": "缺少workflow_id参数"}), 400
        
        sql = """
        SELECT id, merchant, quantity, scan_channel, notes 
        FROM temu_shipment_details 
        WHERE workflow_id = %s 
        ORDER BY id ASC
        """
        shipment_details = db.execute_query(sql, [workflow_id])
        
        return jsonify({
            "success": True, 
            "data": shipment_details
        })
        
    except Exception as e:
        print(f"获取TEMU发货明细数据失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# 批量更新明细表物流状态和实收件数API
@app.route('/api/shipping_allocation_details/batch_update', methods=['POST'])
@login_required
@permission_required('query_function')
def api_batch_update_shipping_details():
    """
    批量更新明细表的物流状态和实收件数
    请求体: { "details": [ { "tracking_number": "...", "logistics_status": "...", "actual_received_count": ... }, ... ] }
    """
    try:
        data = request.get_json()
        details = data.get('details', [])
        
        if not details:
            return jsonify({"success": False, "message": "没有要更新的数据"}), 400

        updated_count = 0
        
        for item in details:
            tracking_number = item.get('tracking_number')
            logistics_status = item.get('logistics_status')
            actual_received_count = item.get('actual_received_count')
            
            if not tracking_number:
                continue
                
            # 根据快递单号更新对应的明细记录
            sql = """
                UPDATE shipping_allocation_details
                SET logistics_status = %s, actual_received_count = %s, updated_at = NOW()
                WHERE main_id IN (
                    SELECT id FROM shipping_allocation_main 
                    WHERE tracking_number = %s AND status = 1
                ) AND status = 1
            """
            
            rows_affected = db.execute_update(sql, [logistics_status, actual_received_count, tracking_number])
            if rows_affected > 0:
                updated_count += 1
                print(f"更新快递单号 {tracking_number}: 物流状态={logistics_status}, 实收件数={actual_received_count}")

        return jsonify({
            "success": True, 
            "updated": updated_count,
            "message": f"成功更新了 {updated_count} 条记录"
        })
        
    except Exception as e:
        print(f"批量更新明细失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# 错误处理
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.route('/acrylic_beads.html')
def acrylic_beads_html():
    """
    显示丙烯酸珠子产品页面
    """
    return render_template('acrylic_beads.html')

@app.route('/ocr_extract.html')
@login_required
@permission_required('ocr_extract_html')
def ocr_extract_html():
    """OCR图片文字提取页面"""
    return render_template('ocr_extract.html')

@app.route('/api/ocr/extract', methods=['POST'])
@login_required
@permission_required('ocr_extract_html')
def api_ocr_extract():
    """OCR图片文字提取API"""
    try:
        # 检查是否有上传的文件
        if 'image' not in request.files:
            return jsonify({'error': '请上传图片文件'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': '请选择图片文件'}), 400
        
        # 获取语言参数
        language = request.form.get('language', 'auto')
        
        # 验证文件类型
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_extensions:
            return jsonify({'error': '不支持的文件格式，请上传PNG、JPG、JPEG、GIF或BMP格式的图片'}), 400
        
        # 保存上传的文件到临时目录
        filename = secure_filename(f"{uuid.uuid4().hex}.{file_ext}")
        upload_path = os.path.join('temp_uploads', filename)
        
        # 确保临时目录存在
        os.makedirs('temp_uploads', exist_ok=True)
        
        file.save(upload_path)
        
        try:
            # 导入OCR库
            import pytesseract
            import easyocr
            from PIL import Image
            import cv2
            import numpy as np
            
            # 图片预处理
            def preprocess_image(image_path):
                """图片预处理以提高OCR识别准确度"""
                image = cv2.imread(image_path)
                
                # 转换为灰度图
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                
                # 高斯模糊降噪
                blurred = cv2.GaussianBlur(gray, (3, 3), 0)
                
                # 自适应阈值二值化
                binary = cv2.adaptiveThreshold(
                    blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, 11, 2
                )
                
                # 形态学操作去除噪点
                kernel = np.ones((2, 2), np.uint8)
                processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
                
                return processed
            
            # 使用两种OCR引擎进行文字识别
            extracted_text = ""
            
            # 方法1: EasyOCR (更准确，支持多种语言)
            try:
                reader = easyocr.Reader(['ch_sim', 'en'] if language in ['zh', 'auto'] else ['en'])
                results = reader.readtext(upload_path)
                easyocr_text = '\n'.join([result[1] for result in results if result[2] > 0.5])  # 置信度过滤
                if easyocr_text.strip():
                    extracted_text = easyocr_text
            except Exception as e:
                print(f"EasyOCR识别失败: {e}")
            
            # 方法2: Tesseract OCR (备选方案)
            if not extracted_text.strip():
                try:
                    # 预处理图片
                    processed_image = preprocess_image(upload_path)
                    
                    # 设置Tesseract配置
                    if language == 'zh':
                        tesseract_config = '--oem 3 --psm 6 -l chi_sim'
                    elif language == 'en':
                        tesseract_config = '--oem 3 --psm 6 -l eng'
                    else:  # auto
                        tesseract_config = '--oem 3 --psm 6 -l chi_sim+eng'
                    
                    # OCR识别
                    tesseract_text = pytesseract.image_to_string(
                        processed_image, 
                        config=tesseract_config
                    ).strip()
                    
                    if tesseract_text:
                        extracted_text = tesseract_text
                        
                except Exception as e:
                    print(f"Tesseract OCR识别失败: {e}")
            
            # 文本后处理
            if extracted_text:
                # 清理文本：去除多余空行，统一换行符
                lines = [line.strip() for line in extracted_text.split('\n')]
                extracted_text = '\n'.join([line for line in lines if line])
            
            return jsonify({
                'success': True,
                'text': extracted_text,
                'method': 'EasyOCR' if extracted_text else 'Tesseract',
                'language': language
            })
            
        except ImportError as e:
            return jsonify({
                'error': f'OCR库未安装：{str(e)}，请先安装pytesseract和easyocr'
            }), 500
            
        except Exception as e:
            print(f"OCR处理错误: {e}")
            return jsonify({'error': f'文字识别失败：{str(e)}'}), 500
            
        finally:
            # 清理临时文件
            try:
                if os.path.exists(upload_path):
                    os.remove(upload_path)
            except Exception as e:
                print(f"清理临时文件失败: {e}")
    
    except Exception as e:
        print(f"OCR API错误: {e}")
        return jsonify({'error': f'服务器错误：{str(e)}'}), 500

# 启动应用
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 