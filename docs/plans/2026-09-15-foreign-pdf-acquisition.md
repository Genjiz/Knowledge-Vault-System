# 外文期刊 PDF 获取实施计划

## 1. 目标与范围

- 为已有统一文献获取合法可访问的英文期刊 PDF，并复用现有全文任务、PDF 资产和论文分析流程。
- 第一阶段只实现 ScienceDirect，使用 Scopus 题录中的 DOI、PII 和详情页作为稳定定位信息。
- 支持文献详情单篇获取、Scopus 卷期批量补采，以及任务因人机校验暂停后的人工恢复。
- 不依赖 Elsevier 全文 API，不绕过登录、订阅、验证码、Cloudflare 或其他访问控制。
- 不接入来源不明的镜像站，不自动搜索或下载版权状态不明确的副本。

当前正式数据中只有外文期刊 `Information Processing & Management`，共 601 篇 Scopus 原始论文；601 篇均有 DOI 和 PII，适合作为首个 ScienceDirect 试点。

## 2. 已确认决策与约束

- PDF 继续归属统一 `literature`，不归属 `raw_issue`；题录与全文任务相互独立。
- 自动获取不得覆盖用户上传 PDF；替换已有自动来源 PDF 必须由用户在单篇入口明确确认。
- Scopus 是题录来源，ScienceDirect 是全文来源。全文解析器独立于题录 `SourceAdapter` 注册表，避免把所有 Scopus 论文误判为 Elsevier 全文。
- 第一版按论文来源信息选择全文提供器：Magtech 关联走 Magtech；PII 或 ScienceDirect 详情页走 ScienceDirect；无法识别时返回明确的不支持原因。
- ScienceDirect 下载默认串行执行，有限重试只覆盖超时和临时服务错误；401、403、验证码、订阅不足等确定性错误不重试。
- 浏览器必须可见，并使用仓库外部提交范围的持久 profile；账号登录和人机校验只允许用户手动完成。
- 浏览器 profile、Cookie、账号和验证码结果不得写入数据库、日志、任务错误信息或可提交产物。
- 本机已检测并获准使用 Edge：`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`。公共运行时探测覆盖 Edge x64/x86 常见路径，也可通过 `CRAWLER_BROWSER_PATH` 覆盖；业务模块不保存浏览器路径。

## 3. 计划复核与风险处理

### 3.1 已补齐的遗漏

- **Cloudflare 出口拒绝不等于验证码**：2026-09-15 实测 ScienceDirect 文章页和 PDF 候选地址均返回 `403`、`server=cloudflare`、正文错误码 `CPE00001`。系统必须将其归类为 `access_blocked`，提示切换校园网、aTrust/VPN 或网络出口，不得循环打开页面。
- **人机校验必须可恢复**：新增 `waiting_user` 任务/条目状态和恢复接口。后台线程遇到 challenge 后结束并保留当前条目；用户手动完成后从当前条目继续，而不是新建任务或重跑已成功论文。
- **浏览器关闭或后端重启**：任务持久保存待处理 URL 和原因；恢复时重新连接或启动受控浏览器。不能依赖后台线程长期阻塞等待。
- **批量熔断**：一篇出现 challenge 或出口拒绝即暂停整批；连续请求不会继续触发风控。
- **订阅不足单独分类**：文章页可访问但没有全文权益时标记 `access_denied`，不提示做人机校验。
- **伪 PDF 防护**：HTML 登录页、challenge 页面、错误页即使 URL 或 Content-Type 像 PDF，也必须通过 PDF 文件头和大小校验后才能落盘。

### 3.2 人机校验流程

1. 下载器识别 challenge URL、页面标题、DOM 标记或响应正文特征。
2. 当前条目标记 `waiting_user`，任务标记 `waiting_user`，保存公开的文章 URL和面向用户的处理说明。
3. 受控、可见的 Chromium 浏览器打开文章页；程序不点击验证码、不调用解码服务。
4. 前端显示“等待人工验证”和“验证完成后继续”操作。
5. 用户完成验证后调用恢复接口；下载器读取同一浏览器 profile 的会话，再次尝试当前论文。
6. 若仍是 challenge，任务继续保持等待；若是出口拒绝或订阅不足，按对应失败类型停止或记录失败。

### 3.3 状态与失败分类

- 任务状态：`pending`、`running`、`waiting_user`、`completed`、`partial`、`failed`。
- 条目状态：`pending`、`running`、`waiting_user`、`completed`、`failed`、`skipped`。
- 失败代码至少包括：`verification_required`、`access_blocked`、`access_denied`、`not_supported`、`not_pdf`、`too_large`、`network_error`、`remote_error`。
- 数据库只保存稳定失败代码、公开 URL 和脱敏说明，不保存响应正文、Cookie、IP、Cloudflare reference number 等会话信息。

## 4. 实施步骤

1. 新增全文提供器接口与注册表，把现有 Magtech 下载包装为提供器，并为 Scopus/PII 选择 ScienceDirect 提供器。
2. 先编写失败测试，覆盖提供器选择、PII 引用、单篇/卷期任务、来源保护和现有 Magtech 兼容。
3. 泛化 `FullTextService`，移除 Magtech 硬编码，保存逐条 provider、失败代码、待处理 URL，并支持 `waiting_user`。
4. 增加数据库迁移，扩展全文任务与条目的恢复状态字段；迁移正式数据库并核对迁移头。
5. 实现 ScienceDirect HTTP 下载器：构造文章页与 PDF 候选地址、有限重试、响应分类、PDF 校验和脱敏错误。
6. 实现受控浏览器网关：复用持久 profile、打开待验证页面、导出当前域会话到 HTTP 下载器；不实现验证码求解。浏览器原生下载只作为验证方向，遇到持续 challenge 时不得加入规避逻辑。
7. 增加任务恢复 API，并在文献详情和 Scopus 期号详情提供状态、失败原因、人工验证提示和恢复按钮。
8. 更新离线单元/API/前端测试，运行完整后端测试、前端测试、生产构建和 chunk 检查。
9. 在校园网或 aTrust/VPN 环境中进行 1 篇授权下载 smoke test；通过后再测试 5 篇和一个期号。
10. 根据验证结果更新当前架构、目标规范、长期决策和工程经验；计划中的长期信息提炼完毕后删除本文件。

## 5. 当前进度

- [x] 提交并推送任务开始前的全部工作区改动：`70724915`。
- [x] 核对现有全文任务、来源注册表、浏览器 profile 和 Scopus 引用覆盖率。
- [x] 实测匿名 HTTP 访问 ScienceDirect，确认当前出口返回 Cloudflare `403 / CPE00001`。
- [x] 完成人机校验、出口拒绝、恢复和熔断方案复核。
- [x] 编写失败测试。
- [x] 实现后端全文提供器和恢复状态机。
- [x] 实现前端人工接管流程。
- [ ] 完成离线与真实环境验证。
- [x] 更新正式文档；因授权下载仍待外部网络验证，暂保留本计划。

## 6. 计划偏差

- 原讨论将 ScienceDirect 的 403 主要视为人机校验；实测表明当前响应是 Cloudflare 出口拒绝页，因此新增 `access_blocked` 分类和批量立即熔断，不能仅依靠用户完成验证码恢复。
- 原讨论倾向直接扩展采集源适配器；复核后改为独立全文提供器注册表，因为 Scopus 可收录多个出版社，题录来源不能决定全文站点。
- 公共浏览器路径探测原先只覆盖 Chrome/Chromium；按本机环境补充 Edge x64/x86 常见路径，并用真实 Edge 完成可见浏览器和会话重连 smoke test。
- 机构登录后的真实 Edge 页面已显示动态 `View PDF` 链接，但 PDF 资产域进入持续 Turnstile；把同一 profile 的 Cookie 和动态链接转入 `requests` 后仍返回 `CPE00001`。因此不实现浏览器原生下载回退或 challenge 规避，继续按 `access_blocked` 暂停，等待用户切换合规网络出口。

## 7. 验证结果

- 任务开始前基线：后端 242 项测试通过；前端 17 项测试通过；生产构建和活动 chunk 限制检查通过。
- ScienceDirect 匿名 HTTP 探测：文章页和 `/pdfft` 候选地址均返回 HTTP 403、HTML 正文、Cloudflare `CPE00001`，未产生文件。
- 后端全量 255 项测试通过；前端 Vitest 19 项、Playwright 14 项、类型检查、ESLint、生产构建和活动 chunk 限制检查均通过。
- 数据库迁移已应用到正式库，Alembic 版本为 `f6b8c1d3e742`；正式 Scopus DOI/PII 覆盖仍为 601/601。
- 受控浏览器成功启动并重连 `Edg/152.0.4191.66`，打开目标公开文章页；恢复侧仅在内存读取会话，没有输出 Cookie 值或写入数据库。
- 正式 IP&M 单篇任务 ID 2 在当前出口下正确停为 `waiting_user / access_blocked`，未写入 PDF。复用 Edge 会话再次探测仍为 `access_blocked`。
- 用户已在专用 profile 完成机构登录，文章页显示 `View PDF`；PDF 资产页进入持续 `cf-chl` / Turnstile，同一动态链接的 HTTP 请求返回 `403 / CPE00001`。停止进一步自动化尝试。

## 8. 遗留问题

- 当前网络出口被 ScienceDirect PDF 资产域拒绝；需要切换校园网或 aTrust/VPN 后，才能验证 1 篇授权 PDF 成功下载。仅完成机构登录不足以解除该出口限制。
- ScienceDirect 在校园网/aTrust 下可能仍要求机构登录；登录由用户手动完成，实际订阅覆盖率需通过小批验证得出。
- 其他出版社与开放仓储不在第一阶段范围内，待 ScienceDirect 流程稳定后按独立提供器扩展。
