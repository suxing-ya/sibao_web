# 货物费用分摊计算网站

## 项目简介
这是一个基于网页的货物费用分摊计算工具，旨在帮助用户高效管理和计算每日发货费用。它允许用户输入货物重量、件数、运费单价等信息，自动计算出每项货物的分摊费用，并支持数据保存、查询和导出功能。**本项目的后端使用 Flask 框架，负责用户认证、页面路由以及与 Supabase 数据库的交互。**

## 主要功能
-   **直观的费用输入**：用户可以输入日期、快递单号、货件ID、运费单价、实重+纸箱等关键信息。
-   **自动计算与汇总**：根据输入的货物实重和抛出重量，自动计算总运费、纸箱重量、抛出重量等，并汇总商户数量。
-   **商户明细管理**：以表格形式展示每个商户的件数、货物实重、分摊比例、占纸箱重量、占抛出重量、结算重量和合计金额。
-   **动态商户添加与删除**：支持在表格中动态添加新的商户记录和删除现有记录。
-   **数据可视化**：通过饼图直观展示各商户的费用分摊比例。
-   **数据持久化 (Supabase)**：将计算结果保存到 Supabase 数据库，实现数据的云端存储和跨设备访问。
-   **历史数据查询**：提供单独的页面查询和管理所有保存的历史数据，支持数据删除。
-   **Excel 导出**：支持将计算结果导出为 Excel 文件，方便数据分析和存档。
-   **通知音效**：保存成功时播放提示音。

## 技术栈
-   **前端**：
    -   HTML5
    -   CSS (Tailwind CSS for样式)
    -   JavaScript (核心逻辑，DOM操作)
    -   Chart.js (用于数据可视化图表)
    -   SheetJS / XLSX (用于Excel文件导出)
    -   SweetAlert2 (用于美观的弹窗提示)
-   **后端/数据库**：
    -   **Python (Flask 框架)**: 负责路由、模板渲染和后端逻辑。
    -   **Supabase**: 作为后端服务，提供PostgreSQL数据库和RESTful API。
    -   `python-dotenv`: 用于加载环境变量。
    -   `supabase-py`: Supabase Python 客户端。
    -   `Werkzeug`: Flask 的依赖，提供 WSGI 工具。
-   **部署**：
    -   **前端**: Vercel (用于前端应用的快速部署和托管)
    -   **后端**: 推荐部署在支持 Python Web 服务（如 Gunicorn/uWSGI）的云平台，例如 Railway, Render, 或传统云服务器。

## 架构与实现逻辑

### 前端部分
-   **`index.html` (主页面)**：
    -   负责用户界面的渲染，包括费用输入表单、汇总信息、费用分布图表和商户明细表格。
    -   通过 JavaScript 监听用户输入和按钮点击事件。
    -   实现各种计算逻辑，如运费分摊、比例计算等。
    -   使用 Chart.js 实时更新费用分布饼图。
    -   集成 SheetJS/XLSX 库，将表格数据导出为 Excel 文件。
    -   **直接通过 Flask 路由提供。数据操作（保存）通过 JavaScript 与 Supabase 数据库进行交互 (`saveData` 函数)。**
-   **`query.html` (历史查询页面)**：
    -   **通过 Flask 路由提供。**负责展示从 Supabase 获取的历史数据。
    -   通过 JavaScript 的 `loadAndRenderHistory` 函数从 Supabase 数据库 `shipping_costs` 表中查询所有数据并渲染到表格中。
    -   实现数据的删除功能，通过 Supabase 的 `delete` 操作。
    -   提供"返回主页"链接，导航回 `index.html`。

### 后端部分 (Flask)
-   **`app.py` (核心后端逻辑)**：
    -   基于 Flask 框架构建，负责处理 HTTP 请求、路由管理和模板渲染。
    -   **用户认证**: 集成 Supabase Auth 进行用户登录、登出和会员管理。使用 `@login_required` 和 `@admin_required` 装饰器实现路由保护。
    -   **页面路由**: 提供多个 HTML 页面的渲染服务，例如 `/`, `/admin/login`, `/admin/dashboard`, `/Expense Allocation Function.html`, `/query.html` 等。
    -   **API 端点**: 暴露 `/api/members` 和 `/api/member/<member_id>` 等 API 端点，用于管理员获取和管理会员信息。
    -   **数据库交互**: 通过 Supabase Python 客户端与 Supabase 数据库进行交互（例如，在管理员仪表板中查询用户和配置文件）。
    -   **环境变量**: 使用 `python-dotenv` 加载 `.env` 文件中的 Supabase 配置信息。
-   **`templates/` 目录**: 存放由 Flask 渲染的 HTML 模板文件（如 `login_admin.html`, `admin.html` 等）。
-   **`requirements.txt`**: 列出了所有 Python 依赖，包括 Flask, Werkzeug, supabase-py 和 python-dotenv。

### 后端/数据库部分 (Supabase)
-   **数据库**：Supabase 提供了一个基于 PostgreSQL 的数据库。
-   **表结构**：创建了一个名为 `shipping_costs` 的表，包含以下列：
    -   `id` (UUID, 主键): 唯一标识每条记录。
    -   `created_at` (timestamp with time zone): 记录创建时间 (Supabase 自动管理)。
    -   `date` (date): 运费记录日期。
    -   `freight_unit_price` (numeric): 运费单价。
    -   `total_settle_weight` (numeric): 总结算重量。
    -   `actual_weight_with_box` (numeric): 实重+纸箱重量。
    -   `tracking_number` (text): 快递单号。
    -   `shipment_id` (text): 货件ID。
    -   `merchants` (jsonb): 存储商户详情的 JSON 数组，包含每个商户的名称、件数、重量等。
-   **API**：Supabase 自动为数据库表生成 RESTful API，前端通过 Supabase JS SDK 调用这些 API 进行数据的 `upsert` (插入/更新) 和 `select` (查询) 操作。
-   **行级安全 (RLS)**：为方便演示和功能实现，`shipping_costs` 表的 RLS 暂时禁用。在生产环境中，强烈建议配置适当的 RLS 策略以保护数据。

## 部署
本网站通过 [Vercel](https://vercel.com/) 进行部署。Vercel 能够与 GitHub 仓库无缝集成，每次推送到 `main` 分支的代码更改都会自动触发新的部署。
-   **域名**：已绑定自定义域名 `www.sibaostudio.com`。
-   **SSL**：Vercel 自动处理 SSL 证书的颁发和续期，确保网站通过 HTTPS 安全访问。

## 如何运行 (本地)
1.  **克隆仓库**：
    ```bash
    git clone git@github.com:suxing-ya/sibao_web.git
    cd sibao_web
    ```
2.  **配置 Supabase**：
    -   确保您有一个 Supabase 项目，并创建了 `shipping_costs` 表，结构如上所述。
    -   在 `index.html` 和 `query.html` 文件中，将 `SUPABASE_URL` 和 `SUPABASE_ANON_KEY` 替换为您自己的 Supabase 项目凭据。
3.  **打开文件**：
    -   直接在浏览器中打开 `index.html` 文件即可运行。

## 未来可能的增强
-   **用户认证**：集成 Supabase Authentication，实现用户登录注册，并为每位用户存储私有数据。
-   **更复杂的权限管理**：配置细粒度的 Supabase RLS 策略，确保数据安全。
-   **高级数据分析**：添加更多图表和报告，提供更深入的费用分析。
-   **响应式优化**：进一步优化移动设备上的用户体验。
-   **离线支持**：利用 Service Worker 实现离线数据存储和同步。

---
**技术支持**：如果您在使用过程中遇到任何问题，欢迎通过 GitHub Issues 提出。 