import os
from supabase import create_client, Client

# 从环境变量获取 Supabase 配置
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("错误：环境变量 SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY 未设置。")
    print("请确保在运行脚本前设置这些环境变量。")
    exit(1)

try:
    # 初始化 Supabase 客户端
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    print("Supabase 客户端初始化成功。")

    # 尝试获取所有用户列表（需要 service_role 权限）
    print("尝试使用 service_role 密钥获取所有用户...")
    auth_users_response = supabase.auth.admin.list_users()

    if auth_users_response:
        print("成功获取用户列表！")
        for user in auth_users_response:
            print(f"  用户ID: {user.id}, 邮箱: {user.email}, 创建时间: {user.created_at}")
        print(f"总计 {len(auth_users_response)} 位用户。")
    else:
        print("未获取到用户，或用户列表为空。")

except Exception as e:
    print(f"发生错误: {e}")
    print("请检查您的 Supabase URL 和 SERVICE_ROLE_KEY 是否正确，以及 service_role 是否具有 auth.users 的 SELECT 权限。")
