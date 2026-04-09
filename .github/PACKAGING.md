# GitHub Actions Build Configuration

## Packaging Workflow

The `.github/workflows/package-release.yml` 工作流在每次发布 (release) 时自动触发，生成以下包：
- **Windows**: `Matched-Betting-Manager.exe` (单文件可执行文件)
- **Linux**: `matched-betting-manager_*.deb` (Debian 包)

### 工作流说明

**触发条件**: 创建新的 GitHub Release 时自动运行

**Windows 构建 (build-exe)**:
- 使用 PyInstaller 打包成单个 EXE 文件
- 会尝试使用 `icon.ico` (如果存在)，否则使用默认图标
- 生成文件自动上传至 Release

**Linux 构建 (build-deb)**:
- 使用 PyInstaller 构建可执行文件
- 使用 fpm 生成标准 Debian 包
- 创建 `.desktop` 文件供桌面环境使用
- 版本号从 git tag 自动提取

### 可选优化

**添加应用图标** (Windows):
1. 将 256x256 像素的 PNG 转换为 `icon.ico`
2. 放在项目根目录
3. 工作流会自动检测并使用

**数据文件打包**:
若需要打包初始数据文件 (如 `data/test_betting_v2.csv`):
```bash
# 添加到 PyInstaller 命令中:
pyinstaller --onefile --windowed \
  --add-data "data:data" \
  --name "Matched-Betting-Manager" \
  main.py
```

### 使用说明

1. **创建 Release**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
   或在 GitHub 网站上手动创建 Release

2. **监控构建**: 在 Actions 标签页查看实时构建日志

3. **下载包**: Release 页面自动包含生成的 EXE 和 DEB 文件
