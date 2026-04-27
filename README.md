<p align="center">
  <a href="https://github.com/mizhexiaoxiao/vue-fastapi-admin">
    <img alt="Vue FastAPI Admin Logo" width="200" src="https://github.com/mizhexiaoxiao/vue-fastapi-admin/blob/main/deploy/sample-picture/logo.svg">
  </a>
</p>

<h1 align="center">vue-fastapi-admin</h1>

[English](./README-en.md) | 简体中文

基于 FastAPI + Vue3 + Naive UI 的现代化前后端分离开发平台，融合了 RBAC 权限管理、动态路由和 JWT 鉴权，助力中小型应用快速搭建，也可用于学习参考。

### 特性
- **最流行技术栈**：基于 Python 3.11 和 FastAPI 高性能异步框架，结合 Vue3 和 Vite 等前沿技术进行开发，同时使用高效的 npm 包管理器 pnpm。
- **代码规范**：项目内置丰富的规范插件，确保代码质量和一致性，有效提高团队协作效率。
- **动态路由**：后端动态路由，结合 RBAC（Role-Based Access Control）权限模型，提供精细的菜单路由控制。
- **JWT鉴权**：使用 JSON Web Token（JWT）进行身份验证和授权，增强应用的安全性。
- **细粒度权限控制**：实现按钮和接口级别的权限控制，确保不同用户或角色在界面操作和接口访问时具有不同的权限限制。

### 当前业务功能

#### 1. 系统管理
- 用户管理：用户新增、编辑、删除、重置密码、角色分配。
- 角色管理：角色权限分配、菜单授权、接口授权。
- 菜单管理：后端动态菜单、前端动态路由、目录/菜单结构维护。
- API管理：接口列表维护与刷新。
- 部门管理：部门树结构与层级维护。
- 审计日志：记录请求参数、响应摘要、响应时间与用户信息。
- 系统设置：
  - 站点标题与 Logo。
  - 工单分类与问题根因配置。
  - SMTP 邮件发送配置与模板配置。
  - WebDAV 外发网盘配置。
  - AI 大模型配置（provider/base_url/api_key/model/timeout）。

#### 2. 工单中心
- 提交工单：
  - 登录用户提交。
  - 游客免登录提交。
  - 验证码校验。
  - 附件上传。
- 我的工单：
  - 查看自己的工单列表与详情。
  - 支持按标题、分类、状态、问题根因筛选。
- 工单审核：
  - 客服审核通过/驳回。
  - 审核时填写备注。
  - 支持快捷筛选与详情查看。
- 技术处理：
  - 技术完成/驳回处理。
  - 完成时必须选择“问题根因”，根因来源于系统设置配置。
  - 支持备注填写、快捷筛选与详情查看。
- 工单详情增强：
  - 统一详情弹窗。
  - 展示基础信息、问题描述、流转时间线、附件列表。
  - 附件通过后端受控接口下载。
  - 显示客服审核人、技术处理人、完成时间、问题根因。

#### 3. 代理商/注册审核
- 支持渠道商/用户注册申请。
- 支持客服/管理员审核通过或驳回。
- 支持验证码邮件、审核通知邮件模板化发送。

#### 4. 外发管理（WebDAV）
- 外发管理一级菜单。
- 外发网盘：
  - 只读浏览目录与文件。
  - 支持目录层级跳转与面包屑导航。
  - 支持为文件创建分享链接。
- 分享记录：
  - 独立菜单展示。
  - 默认只看有效分享，可切换查看历史记录。
  - 下载链接复制、分享删除。
  - 管理员可查看所有分享记录，普通用户仅查看自己的记录。
- 分享规则：
  - 同一用户对同一文件重复创建分享时，若已有有效链接则直接复用。
  - 分享下载支持中文文件名与安全的 `Content-Disposition` 响应头。
- 缓存与稳定性：
  - WebDAV 列表结果缓存到 Redis，默认 1 天。
  - 上传/创建目录/删除后自动失效相关缓存。
  - 统一处理认证失败、路径不存在、资源冲突、资源锁定、超时、连接异常等错误。

#### 5. AI 知识库
- AI 知识库一级菜单。
- 知识空间：知识空间创建、更新、列表查询。
- 文档中心：
  - 手工录入文档。
  - 文件上传文档。
  - 文档重解析。
  - 软删除文档。
  - 处理待解析文档。
  - 支持按空间、关键字、解析状态、来源类型筛选。
- 文档解析与去重：
  - 手工录入正文会真实落盘到存储目录。
  - 文档计算 `file_hash`，同空间下重复正文/重复文件可复用已有文档。
  - 已支持文本、Markdown、CSV、JSON、PDF、DOCX 的最小文本提取能力。
- 智能问答：
  - 会话创建与会话列表。
  - 基于知识片段的问答回答。
  - 返回引用片段、模型名、耗时、token 统计。
- 反馈标注：对回答进行反馈记录。
- 模型日志：
  - 记录 LLM 调用 provider、model、tokens、耗时、错误码。
  - 支持请求/响应详情查看。
  - 支持模型连通性测试。

#### 6. 配置驱动能力
- 工单分类、问题根因、大模型配置全部由系统设置统一维护。
- WebDAV、邮件模板、AI 模型均支持后台配置后即时生效。

### 在线预览
- [http://47.111.145.81:3000](http://47.111.145.81:3000)
- username: admin
- password: 123456

### 登录页

![image](https://github.com/mizhexiaoxiao/vue-fastapi-admin/blob/main/deploy/sample-picture/login.jpg)
### 工作台

![image](https://github.com/mizhexiaoxiao/vue-fastapi-admin/blob/main/deploy/sample-picture/workbench.jpg)

### 用户管理

![image](https://github.com/mizhexiaoxiao/vue-fastapi-admin/blob/main/deploy/sample-picture/user.jpg)
### 角色管理

![image](https://github.com/mizhexiaoxiao/vue-fastapi-admin/blob/main/deploy/sample-picture/role.jpg)

### 菜单管理

![image](https://github.com/mizhexiaoxiao/vue-fastapi-admin/blob/main/deploy/sample-picture/menu.jpg)

### API管理

![image](https://github.com/mizhexiaoxiao/vue-fastapi-admin/blob/main/deploy/sample-picture/api.jpg)

### 快速开始
#### 方法一：dockerhub拉取镜像

```sh
docker pull mizhexiaoxiao/vue-fastapi-admin:latest 
docker run -d --restart=always --name=vue-fastapi-admin -p 9999:80 mizhexiaoxiao/vue-fastapi-admin
```

#### 方法二：dockerfile构建镜像
##### docker安装(版本17.05+)

```sh
yum install -y docker-ce
systemctl start docker
```

##### 构建镜像

```sh
git clone https://github.com/mizhexiaoxiao/vue-fastapi-admin.git
cd vue-fastapi-admin
docker build --no-cache . -t vue-fastapi-admin
```

##### 启动容器

```sh
docker run -d --restart=always --name=vue-fastapi-admin -p 9999:80 vue-fastapi-admin
```

##### 访问

http://localhost:9999

username：admin

password：123456

### 本地启动
#### 后端
启动项目需要以下环境：
- Python 3.11

#### 方法一（推荐）：使用 uv 安装依赖
1. 安装 uv
```sh
pip install uv
```

2. 创建并激活虚拟环境
```sh
uv venv
source .venv/bin/activate  # Linux/Mac
# 或
.\.venv\Scripts\activate  # Windows
```

3. 安装依赖
```sh
uv add pyproject.toml
```

4. 启动服务
```sh
python run.py
```

#### 方法二：使用 Pip 安装依赖
1. 创建虚拟环境
```sh
python3 -m venv venv
```

2. 激活虚拟环境
```sh
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

3. 安装依赖
```sh
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

4. 启动服务
```sh
python run.py
```

服务现在应该正在运行，访问 http://localhost:9999/docs 查看API文档

#### 登录密码 RSA 配置（公钥加密密码）

当启用登录密码 RSA 解密时，前端会从 `/api/v1/base/public_config` 获取公钥，并在登录前对密码进行 RSA-OAEP(SHA256) 加密。

1. 在运行环境中设置私钥（推荐环境变量或 `.env`，不要写死到 `app/settings/config.py`）：

```env
LOGIN_PASSWORD_RSA_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
```

2. 重启后端服务。

3. 自检公钥是否生效（PowerShell）：

```powershell
$r = Invoke-RestMethod "http://127.0.0.1:8000/api/v1/base/public_config"
$r.data.login_password_public_key
```

预期返回内容包含 `-----BEGIN PUBLIC KEY-----`。

说明：

- 未配置 `LOGIN_PASSWORD_RSA_PRIVATE_KEY` 时，系统会保持兼容模式（不强制密码密文）。
- 若把私钥直接写到 `Settings` 类字段且缺少类型注解，会触发 Pydantic v2 报错；请保持 `LOGIN_PASSWORD_RSA_PRIVATE_KEY: str = ""`，真实值放环境变量。

#### 生产环境密钥轮换建议

1. 采用双阶段轮换：先发布新公钥（服务端切新私钥并兼容短时会话），再逐步淘汰旧会话。
2. 轮换窗口内缩短登录会话有效期，降低旧密钥影响面。
3. 私钥仅放密钥管理系统/环境变量，严禁提交到仓库与镜像。
4. 轮换后执行回归：`public_config` 公钥返回、登录成功率、解密失败率、审计日志异常比率。
5. 预留应急回滚：保留上一版配置快照，异常时可快速恢复并重启服务。

#### 前端
启动项目需要以下环境：
- node v18.8.0+

1. 进入前端目录
```sh
cd web
```

2. 安装依赖(建议使用pnpm: https://pnpm.io/zh/installation)
```sh
npm i -g pnpm # 已安装可忽略
pnpm i # 或者 npm i
```

3. 启动
```sh
pnpm dev
```

### 目录说明

```
├── app                   // 应用程序目录
│   ├── api               // API接口目录
│   │   └── v1            // 版本1的API接口
│   │       ├── apis      // API相关接口
│   │       ├── base      // 基础信息接口
│   │       ├── menus     // 菜单相关接口
│   │       ├── roles     // 角色相关接口
│   │       └── users     // 用户相关接口
│   ├── controllers       // 控制器目录
│   ├── core              // 核心功能模块
│   ├── log               // 日志目录
│   ├── models            // 数据模型目录
│   ├── schemas           // 数据模式/结构定义
│   ├── settings          // 配置设置目录
│   └── utils             // 工具类目录
├── deploy                // 部署相关目录
│   └── sample-picture    // 示例图片目录
└── web                   // 前端网页目录
    ├── build             // 构建脚本和配置目录
    │   ├── config        // 构建配置
    │   ├── plugin        // 构建插件
    │   └── script        // 构建脚本
    ├── public            // 公共资源目录
    │   └── resource      // 公共资源文件
    ├── settings          // 前端项目配置
    └── src               // 源代码目录
        ├── api           // API接口定义
        ├── assets        // 静态资源目录
        │   ├── images    // 图片资源
        │   ├── js        // JavaScript文件
        │   └── svg       // SVG矢量图文件
        ├── components    // 组件目录
        │   ├── common    // 通用组件
        │   ├── icon      // 图标组件
        │   ├── page      // 页面组件
        │   ├── query-bar // 查询栏组件
        │   └── table     // 表格组件
        ├── composables   // 可组合式功能块
        ├── directives    // 指令目录
        ├── layout        // 布局目录
        │   └── components // 布局组件
        ├── router        // 路由目录
        │   ├── guard     // 路由守卫
        │   └── routes    // 路由定义
        ├── store         // 状态管理(pinia)
        │   └── modules   // 状态模块
        ├── styles        // 样式文件目录
        ├── utils         // 工具类目录
        │   ├── auth      // 认证相关工具
        │   ├── common    // 通用工具
        │   ├── http      // 封装axios
        │   └── storage   // 封装localStorage和sessionStorage
        └── views         // 视图/页面目录
            ├── error-page // 错误页面
            ├── login      // 登录页面
            ├── profile    // 个人资料页面
            ├── system     // 系统管理页面
            └── workbench  // 工作台页面
```

### 进群交流
进群的条件是给项目一个star，小小的star是作者维护下去的动力。

你可以在群里提出任何疑问，我会尽快回复答疑。

<img width="300" src="https://github.com/mizhexiaoxiao/vue-fastapi-admin/blob/main/deploy/sample-picture/group.jpg">

## 打赏
如果项目有帮助到你，可以请作者喝杯咖啡~

<div style="display: flex">
    <img src="https://github.com/mizhexiaoxiao/vue-fastapi-admin/blob/main/deploy/sample-picture/1.jpg" width="300">
    <img src="https://github.com/mizhexiaoxiao/vue-fastapi-admin/blob/main/deploy/sample-picture/2.jpg" width="300">
</div>

## 定制开发
如果有基于该项目的定制需求或其他合作，请添加下方微信，备注来意

<img width="300" src="https://github.com/mizhexiaoxiao/vue-fastapi-admin/blob/main/deploy/sample-picture/3.jpg">

### Visitors Count

<img align="left" src = "https://profile-counter.glitch.me/vue-fastapi-admin/count.svg" alt="Loading">
