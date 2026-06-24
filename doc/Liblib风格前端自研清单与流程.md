# Liblib 风格前端自研清单与流程

面向：公司准备自研一套「无限画布 + 云端 AI API + 创作工作台」产品，前端视觉参考 Liblib / LibTV 的暗色创作平台与无限画布体验。

> 合规前提：本项目只能作为产品样机和流程参考。自研项目必须新建独立仓库，不复制 Infinite Canvas 源码、Liblib 页面素材、截图、Logo、文案和样式文件。对外商用前需确认代码独立，或取得原作者授权。

---

## 一、产品目标

第一期目标不是复刻完整 Liblib 平台，而是做出一个能内部试用的创作工作台：

```text
首页/工作台
  -> 新建项目或画布
  -> 进入暗色无限画布
  -> 选择创作类型节点
  -> 配置 Prompt / 图片 / 模型参数
  -> 调用云端 API
  -> Output 展示图片或视频结果
  -> 保存到素材库或项目
```

第一期只保证「文生图 / 图生图」主流程跑通；视频、LLM、素材库、模板广场放第二期。

---

## 二、视觉方向

### 2.1 首页/工作台参考

参考 Liblib 首页截图，做暗色创作平台布局：

- 顶部窄公告条：活动、模型更新、额度提醒。
- 顶部导航：Logo、创作入口、会员/额度、用户菜单。
- 中央 Banner：模型活动、热门模板、官方推荐。
- 个人最近项目：新建项目卡片、最近画布卡片。
- 模板/案例瀑布流：图片卡片、视频卡片、标签筛选、搜索框。
- 整体风格：深色背景、低饱和卡片、8px 圆角、轻边框、图片内容为主。

第一期可以先用静态假数据，不急着做社区、排行榜、创作者主页。

### 2.2 无限画布参考

参考 Liblib 画布截图：

- 全屏黑色点阵网格背景。
- 左上角：项目名、画布名、下拉切换。
- 右上角：分享、保存状态、会员/额度、用户头像。
- 画布中央空状态：提示「双击画布自由生成节点」。
- 中央快捷卡片：故事脚本生成、角色三视图、首帧图生视频、音频生视频。
- 底部中间悬浮工具栏：新增节点、连接/布局、历史、帮助。
- 左下角：资产管理、缩放比例、快捷入口。
- 节点卡片：深色玻璃质感，带缩略图、模型图标、状态灯、运行按钮。

第一期只做核心画布，不做复杂动画和社区展示。

---

## 三、页面清单

| 页面 | 路由建议 | 第一期 | 说明 |
|---|---|---:|---|
| 登录页 | `/login` | 可选 | 内部试点可先用简单 Token |
| 工作台首页 | `/` 或 `/workspace` | P0 | 类 Liblib 首页，展示项目、画布、模板入口 |
| 项目列表 | `/projects` | P0 | 项目、画布、回收站，可合并进工作台 |
| 无限画布 | `/canvas/:id` | P0 | 核心编辑器 |
| API 设置 | `/settings/providers` | P0 | Provider、Key、模型列表 |
| 素材库 | `/assets` | P1 | 图片/视频素材管理 |
| 模板库 | `/templates` | P1 | 工作流模板、官方示例 |
| 任务中心 | `/tasks` | P1 | 生成中、失败、历史任务 |
| 管理后台 | `/admin` | P2 | 用户、额度、审计、成本 |

---

## 四、第一期 MVP 功能边界

### 4.1 必做 P0

- 工作台首页：暗色布局、最近项目、最近画布、新建入口。
- 无限画布：React Flow 画布、点阵背景、缩放、平移、拖拽、连线。
- 节点类型：`prompt`、`image`、`generator`、`output`。
- 节点快捷创建：双击画布、底部工具栏、空状态快捷卡片。
- 运行流程：Prompt -> Generator -> Output。
- Provider 设置：Base URL、API Key、模型名、验证连接。
- 生图任务：创建任务、轮询状态、展示结果。
- 画布保存：nodes、edges、viewport、title。
- 上传图片：参考图上传并传给生成节点。

### 4.2 第二期 P1

- 视频节点：文生视频、图生视频。
- LLM 节点：Prompt 改写、图文理解、脚本生成。
- Loop 节点：批量生成。
- 素材库：分类、标签、收藏、从 Output 入库。
- 模板库：首页展示模板卡片，一键创建画布。
- 任务中心：失败重试、取消任务、历史记录。
- WebSocket：任务完成主动推送。

### 4.3 暂不做

- 社区广场、公开发布、创作者主页。
- 会员支付、积分商城、对外计费。
- 多人实时协同编辑。
- 本地 ComfyUI / GPU。
- 复杂视频剪辑时间线。
- 对 Liblib 页面像素级复刻。

---

## 五、前端技术选型

| 层级 | 推荐 |
|---|---|
| 框架 | Vite + React + TypeScript |
| 画布 | React Flow |
| 状态 | Zustand |
| 样式 | Tailwind CSS |
| 表单 | React Hook Form 或轻量自写 |
| 图标 | lucide-react |
| 请求 | fetch 封装或 TanStack Query |
| 拖拽上传 | 原生 input + dropzone |
| 后期图像密集层 | 可选 PixiJS，不放第一期主链路 |

选择 React Flow 的原因：第一期核心是节点工作流，不是游戏级渲染。React Flow 能直接处理节点、端口、连线、缩放、框选和自定义 React 节点，开发速度更快。

---

## 六、前端目录结构

```text
frontend/
├── src/
│   ├── app/
│   │   ├── router.tsx
│   │   └── providers.tsx
│   ├── pages/
│   │   ├── WorkspacePage.tsx
│   │   ├── CanvasPage.tsx
│   │   ├── ProviderSettingsPage.tsx
│   │   ├── AssetLibraryPage.tsx
│   │   └── TemplateGalleryPage.tsx
│   ├── components/
│   │   ├── layout/
│   │   ├── workspace/
│   │   ├── canvas/
│   │   ├── nodes/
│   │   └── ui/
│   ├── api/
│   │   ├── client.ts
│   │   ├── providers.ts
│   │   ├── canvases.ts
│   │   ├── tasks.ts
│   │   └── uploads.ts
│   ├── stores/
│   │   ├── canvasStore.ts
│   │   └── workspaceStore.ts
│   ├── types/
│   │   ├── canvas.ts
│   │   ├── provider.ts
│   │   └── task.ts
│   └── styles/
│       └── globals.css
└── package.json
```

---

## 七、核心数据结构

### 7.1 Canvas

```ts
export type CanvasDocument = {
  id: string;
  title: string;
  projectId: string;
  viewport: { x: number; y: number; zoom: number };
  nodes: CanvasNode[];
  edges: CanvasEdge[];
  createdAt: string;
  updatedAt: string;
};
```

### 7.2 Node

```ts
export type CanvasNode =
  | PromptNode
  | ImageNode
  | GeneratorNode
  | OutputNode;

export type NodeStatus = 'idle' | 'running' | 'success' | 'error';
```

### 7.3 Generator 节点

```ts
export type GeneratorNodeData = {
  providerId: string;
  model: string;
  size: '1024x1024' | '1024x1536' | '1536x1024';
  promptMode: 'upstream' | 'manual';
  manualPrompt?: string;
  referenceImageIds?: string[];
  status: NodeStatus;
  taskId?: string;
  error?: string;
};
```

---

## 八、页面流程

### 8.1 工作台首页流程

```text
打开首页
  -> 拉取当前用户/内部 Token 状态
  -> 拉取项目列表、最近画布、模板推荐
  -> 用户点击「新建画布」
  -> 创建 canvas
  -> 跳转 /canvas/:id
```

首页第一期用三块内容即可：

- 最近项目
- 最近画布
- 推荐模板入口

### 8.2 无限画布空状态流程

```text
进入空画布
  -> 显示点阵背景
  -> 中央显示快捷节点卡片
  -> 用户点击「文生图」
  -> 自动创建 Prompt + Generator + Output 三节点并连线
  -> 用户输入 Prompt
  -> 点击运行
```

### 8.3 节点运行流程

```text
点击 Generator 或 Output 的运行按钮
  -> 根据 edges 查找上游节点
  -> 收集 prompt 文本
  -> 收集 image 节点图片
  -> 校验 provider/model
  -> POST /api/canvas-image-tasks
  -> 节点状态改为 running
  -> 轮询 GET /api/canvas-image-tasks/{task_id}
  -> completed 后把图片 URL 写入 Output 节点
  -> 保存画布
```

### 8.4 API 设置流程

```text
进入 Provider 设置页
  -> 新增 Provider
  -> 填 Base URL / API Key / 协议类型
  -> 点击验证连接
  -> 拉取模型列表
  -> 勾选可用模型
  -> 保存配置
  -> 画布 Generator 节点可选择该 Provider
```

---

## 九、接口依赖清单

| 接口 | 方法 | 第一期 | 用途 |
|---|---|---:|---|
| `/health` | GET | P0 | 前后端连通性 |
| `/api/providers` | GET/PUT | P0 | Provider 配置 |
| `/api/providers/test-connection` | POST | P0 | 验证 Key |
| `/api/providers/fetch-models` | POST | P0 | 拉取模型 |
| `/api/canvases` | GET/POST | P0 | 画布列表/创建 |
| `/api/canvases/:id` | GET/PUT | P0 | 画布读写 |
| `/api/ai/upload` | POST | P0 | 参考图上传 |
| `/api/canvas-image-tasks` | POST | P0 | 创建生图任务 |
| `/api/canvas-image-tasks/:id` | GET | P0 | 查询任务 |
| `/api/canvas-video` | POST | P1 | 视频生成 |
| `/api/canvas-llm` | POST | P1 | LLM 节点 |
| `/api/assets` | GET/POST | P1 | 素材库 |

---

## 十、按周开发流程

### Week 0：设计与准备

- [ ] 新建独立仓库，不 fork 当前项目。
- [ ] 确认产品名、Logo、基础视觉，不使用 Liblib 或 Infinite Canvas 素材。
- [ ] 确认技术栈：React + React Flow + FastAPI。
- [ ] 确认第一期只做文生图 / 图生图。
- [ ] 准备至少一个可用的官方或正规聚合 API Key。

交付：产品范围表、接口草图、前端低保真线框图。

### Week 1：前端框架与工作台首页

- [ ] 创建 Vite React TS 项目。
- [ ] 配置 Tailwind、路由、基础布局。
- [ ] 实现暗色主题变量。
- [ ] 实现工作台首页：公告条、导航、Banner、最近项目、最近画布。
- [ ] 用 mock 数据完成页面。

交付：首页可打开，视觉接近暗色创作平台。

### Week 2：API 设置页与后端 Provider

- [ ] 后端实现 `/health`。
- [ ] 后端实现 Provider 配置读写。
- [ ] 后端实现测试连接和模型拉取。
- [ ] 前端实现 Provider 设置页。
- [ ] 前后端联调。

交付：能保存 Provider，能验证 Key。

### Week 3：React Flow 画布骨架

- [ ] 实现 `/canvas/:id` 页面。
- [ ] 接入 React Flow。
- [ ] 实现点阵背景、左上角标题、右上角用户区、底部工具栏。
- [ ] 实现空状态快捷节点卡片。
- [ ] 实现 Prompt / Image / Generator / Output 节点占位。

交付：能创建节点、拖动节点、连线。

### Week 4：画布 CRUD 与上传

- [ ] 后端实现画布创建、读取、保存。
- [ ] 前端实现保存、加载、自动保存。
- [ ] 后端实现图片上传。
- [ ] Image 节点支持上传图片。
- [ ] 刷新页面后画布状态保持。

交付：画布可持久化，图片可上传。

### Week 5：生图任务联调

- [ ] 后端实现 `POST /api/canvas-image-tasks`。
- [ ] 后端实现任务状态持久化。
- [ ] 后端调用上游 API 并保存生成图片。
- [ ] 前端 Generator 节点创建任务。
- [ ] 前端轮询任务并更新节点状态。

交付：浏览器画布内生成第一张图片。

### Week 6：Output、错误处理与内部试用

- [ ] Output 节点展示生成结果。
- [ ] 支持下载、复制 Prompt、再次运行。
- [ ] 统一错误 Toast。
- [ ] Key 错误、超时、上游失败有清晰提示。
- [ ] 部署到内网给 3～5 人试用。

交付：内部 MVP 可用。

### Week 7～8：体验打磨

- [ ] 优化节点尺寸、状态、按钮、工具栏。
- [ ] 添加模板快捷创建：文生图、图生图、海报生成。
- [ ] 添加最近生成记录。
- [ ] 添加基础备份脚本。
- [ ] 整理用户使用说明。

交付：MVP 交付版。

### Week 9～12：第二期

- [ ] Video 节点。
- [ ] LLM 节点。
- [ ] Loop 节点。
- [ ] 素材库页面。
- [ ] 模板库页面。
- [ ] 任务中心。

交付：覆盖团队 80% 日常创作流程。

---

## 十一、前端组件清单

### 工作台

- [ ] `TopNoticeBar`
- [ ] `WorkspaceHeader`
- [ ] `HeroCarousel`
- [ ] `RecentProjectList`
- [ ] `RecentCanvasGrid`
- [ ] `TemplateCardGrid`
- [ ] `CreateCanvasCard`

### 画布

- [ ] `CanvasShell`
- [ ] `CanvasTopLeft`
- [ ] `CanvasTopRight`
- [ ] `CanvasBottomToolbar`
- [ ] `CanvasEmptyStarter`
- [ ] `NodeCreateMenu`
- [ ] `PromptNode`
- [ ] `ImageNode`
- [ ] `GeneratorNode`
- [ ] `OutputNode`
- [ ] `NodeStatusBadge`
- [ ] `TaskProgress`

### 设置

- [ ] `ProviderList`
- [ ] `ProviderForm`
- [ ] `ModelSelector`
- [ ] `ConnectionTestButton`

---

## 十二、验收标准

### 第一阶段验收

- [ ] 首页视觉为暗色创作平台风格。
- [ ] 用户能从首页创建画布。
- [ ] 空画布有 Liblib 类似的中央快捷创建区。
- [ ] 用户能创建 Prompt、Image、Generator、Output 四类节点。
- [ ] 用户能连线并保存画布。
- [ ] 用户能配置 Provider。
- [ ] 用户能在画布内生成图片。
- [ ] 生成失败时能看到明确错误。
- [ ] 刷新页面后节点、连线、结果还在。

### 不通过标准

- [ ] 需要复制当前项目 `canvas.js` 才能实现。
- [ ] API Key 暴露在浏览器。
- [ ] 只能在本地假数据跑，不能联调真实 API。
- [ ] 页面像 Liblib 但没有画布生图闭环。

---

## 十三、参考当前项目时只看什么

| 目的 | 可参考 | 不要复制 |
|---|---|---|
| 画布产品能力 | 节点类型、工具栏位置、资产库入口 | `static/js/canvas.js` 实现 |
| 接口形态 | `/api/canvas-image-tasks`、`/api/canvases` 概念 | `main.py` 路由代码 |
| Provider 配置 | Base URL、Key、模型列表字段概念 | `api-settings.js` 具体代码 |
| 资产库 | 分类、上传、输出入库流程 | CSS/HTML/JS 原文件 |

当前项目适合作为「需求样机」和「接口流程参考」。自研项目建议用 React Flow 和模块化 FastAPI 重新实现。

---

## 十四、费用与人员估算

| 配置 | 第一阶段周期 | 费用估算 |
|---|---:|---:|
| 1 全栈 + AI 辅助 | 10～14 周 | 15～40 万 |
| 1 前端 + 1 后端 | 6～8 周 | 30～70 万 |
| 2 前端 + 2 后端 + 产品/设计兼职 | 8～12 周 | 60～120 万 |

运行成本另算：

- 云服务器/数据库/Redis：1000～8000 元/月。
- 对象存储/CDN：200～3000 元/月。
- AI API 测试额度：5000～20000 元/月。
- 视频生成开放后成本会明显上升，建议第二期再做。

---

## 十五、下一步决策

开工前只需要确认 5 件事：

1. 第一版是否只做内部使用。
2. 第一版是否只做图片生成，不做视频。
3. 是否采用 React Flow。
4. 第一版使用哪个 Provider。
5. 是否先做纯前端高保真原型，再接后端。

推荐答案：

```text
内部使用 + 只做图片 + React Flow + 一个 OpenAI 兼容 Provider + 前端原型和后端并行
```

