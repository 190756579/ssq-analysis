# 双色球概率分析 - GitHub Actions 部署指南

## 功能

每周一/三/五 **北京时间 09:00** 自动运行，结果发邮件到 `190756579@qq.com`。

完全跑在 GitHub 云服务器上，本地电脑**不需要开机**。

## 部署步骤

### 第1步：创建 GitHub 仓库

1. 打开 [https://github.com/new](https://github.com/new)
2. 仓库名随便填，比如 `ssq-analysis`
3. 选 **Public**（免费）或 **Private**
4. 点 **Create repository**

### 第2步：上传代码到仓库

把本仓库的所有文件（`ssq_scheduler.py`、`.github/workflows/ssq_analysis.yml`）推送到 GitHub。

### 第3步：设置 Secrets（SMTP 密码）

1. 进入仓库页面 → **Settings** → **Secrets and variables** → **Actions**
2. 点 **New repository secret**，添加两个：

| Name | Value |
|------|-------|
| `SMTP_USER` | `190756579@qq.com` |
| `SMTP_PASS` | `mbvvsscxcgykbiei`（QQ邮箱授权码） |

### 第4步：启用 GitHub Actions

1. 进入仓库 → **Actions** 标签
2. 如果看到工作流被禁用，点 **Enable workflow**
3. 可以点 **Run workflow** → **Run** 手动触发一次测试

### 第5步：验证

等运行完成后（约2-3分钟）：
- 去 `190756579@qq.com` 收邮件
- 或去仓库 → **Actions** → 最新运行 → **Artifacts** 下载 `ssq-report`

## 定时说明

- **北京时间 09:00** = UTC 时间 01:00
- GitHub Actions 的 cron 用 UTC 时间，已自动换算
- 每周一、三、五自动触发
- 也可在 **Actions** 页面手动点击 **Run workflow** 随时触发

## 文件说明

```
ssq_scheduler.py            ← 主分析脚本（本地运行 + GitHub Actions 都能用）
.github/workflows/ssq_analysis.yml  ← GitHub Actions 自动运行配置
ssq_report.html              ← 运行后生成的报告（自动邮件发送）
```
