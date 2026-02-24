# SRF 文档

Sanic RESTful Framework 的完整文档（支持中英文切换）。

## 文档结构

```
docs/
├── mkdocs.yml                    # MkDocs 配置文件
├── .gitignore                    # 忽略 site 目录
├── translate_docs.py             # 文档翻译脚本
└── source/                       # 文档源文件目录
    ├── zh/                       # 中文文档
    │   ├── index.md              # 主页
    │   ├── features.md           # 特点
    │   ├── api-reference.md      # API 参考
    │   ├── config.md             # 配置项
    │   ├── release-notes.md      # 发布说明
    │   └── usage/                # 用法
    │       ├── getting-started.md    # 快速开始
    │       ├── project-setup.md      # 项目设置
    │       ├── core/                 # 核心概念
    │       └── advanced/             # 高级功能
    │
    └── en/                       # 英文文档（结构同中文）
        ├── index.md
        ├── features.md
        └── ...
```

## 本地预览

### 安装依赖

```bash
conda activate srf
pip install mkdocs mkdocs-material mkdocstrings[python] mkdocs-i18n
```

### 启动开发服务器

```bash
cd docs
mkdocs serve -a 0.0.0.0:8001
```

访问：http://localhost:8001

### 构建静态文件（可选）

```bash
cd docs
mkdocs build
```

注意：`site/` 目录已在 `.gitignore` 中忽略，不会提交到版本控制。

## 多语言支持

本文档使用 `mkdocs-i18n` 插件实现中英文切换：

- **默认语言**: 中文 (zh)
- **支持语言**: 中文、English
- **语言切换**: 在页面右上角可以切换语言

### 工作原理

1. 中文文档位于 `source/zh/` 目录
2. 英文文档位于 `source/en/` 目录
3. 插件会自动为每个页面添加语言切换链接
4. 如果某个页面没有对应语言版本，会显示提示信息

## 文档特点

✅ **多语言支持** - 支持中英文切换  
✅ **完整覆盖** - 涵盖 SRF 所有功能模块  
✅ **简洁示例** - 代码示例简洁明了  
✅ **结构清晰** - 按照功能模块组织  
✅ **链接正确** - 所有内部链接已修正  
✅ **实用场景** - 基于真实业务场景的示例
